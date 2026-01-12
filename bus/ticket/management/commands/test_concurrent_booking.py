from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from ticket.models import Schedule, Bus, Route
from ticket.services import SeatBookingService
import threading
import time
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Test concurrent seat booking to verify transaction-based locking prevents double-booking'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of concurrent users to simulate (default: 5)'
        )
        parser.add_argument(
            '--seats',
            type=int,
            default=2,
            help='Number of seats each user tries to book (default: 2)'
        )
        parser.add_argument(
            '--schedule-id',
            type=int,
            help='Specific schedule ID to test (optional)'
        )

    def handle(self, *args, **options):
        num_users = options['users']
        seats_per_user = options['seats']
        schedule_id = options['schedule_id']
        
        self.stdout.write(f'Testing concurrent booking with {num_users} users, {seats_per_user} seats each')
        
        # Get or create test users
        users = self._get_or_create_test_users(num_users)
        
        # Get a schedule to test
        schedule = self._get_test_schedule(schedule_id)
        if not schedule:
            self.stdout.write(self.style.ERROR('No suitable schedule found for testing'))
            return
        
        self.stdout.write(f'Testing with schedule: {schedule}')
        self.stdout.write(f'Bus capacity: {schedule.bus.capacity}')
        
        # Check initial seat availability
        initial_seats = SeatBookingService.get_available_seats(schedule.id)
        self.stdout.write(f'Initial available seats: {len(initial_seats["available_seats"])}')
        
        # Simulate concurrent booking
        results = self._simulate_concurrent_booking(users, schedule, seats_per_user)
        
        # Display results
        self._display_results(results, schedule, seats_per_user)
        
        # Clean up test data
        self._cleanup_test_data(users, schedule)

    def _get_or_create_test_users(self, num_users):
        """Create test users for concurrent booking simulation"""
        users = []
        for i in range(num_users):
            username = f'test_user_{i+1}'
            email = f'test{i+1}@example.com'
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': f'Test{i+1}',
                    'last_name': 'User',
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'Created test user: {username}')
            else:
                self.stdout.write(f'Using existing test user: {username}')
            
            users.append(user)
        
        return users

    def _get_test_schedule(self, schedule_id=None):
        """Get a suitable schedule for testing"""
        if schedule_id:
            try:
                return Schedule.objects.get(id=schedule_id)
            except Schedule.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Schedule {schedule_id} not found'))
                return None
        
        # Find a schedule with enough available seats
        future_schedules = Schedule.objects.filter(
            departure_time__gt=timezone.now() + timedelta(hours=1)
        ).select_related('bus')
        
        for schedule in future_schedules:
            try:
                seat_info = SeatBookingService.get_available_seats(schedule.id)
                if seat_info['available_count'] >= 10:  # Need at least 10 seats for testing
                    return schedule
            except:
                continue
        
        return None

    def _simulate_concurrent_booking(self, users, schedule, seats_per_user):
        """Simulate multiple users booking seats simultaneously"""
        results = []
        threads = []
        
        def book_seats_for_user(user, user_index):
            """Function to be executed by each thread"""
            try:
                # Generate random seat numbers
                available_seats = SeatBookingService.get_available_seats(schedule.id)
                if len(available_seats['available_seats']) < seats_per_user:
                    results.append({
                        'user': user.username,
                        'success': False,
                        'error': 'Not enough seats available',
                        'seats_requested': seats_per_user
                    })
                    return
                
                # Select random seats
                selected_seats = random.sample(available_seats['available_seats'], seats_per_user)
                
                # Try to book seats
                start_time = time.time()
                booking_result = SeatBookingService.book_seats_with_lock(
                    schedule_id=schedule.id,
                    user=user,
                    passenger_name=f'Test Passenger {user_index+1}',
                    passenger_email=user.email,
                    passenger_phone='01234567890',
                    seat_numbers=selected_seats
                )
                end_time = time.time()
                
                results.append({
                    'user': user.username,
                    'success': True,
                    'booking_id': booking_result['booking'].id,
                    'seats_booked': selected_seats,
                    'time_taken': end_time - start_time
                })
                
            except Exception as e:
                results.append({
                    'user': user.username,
                    'success': False,
                    'error': str(e),
                    'seats_requested': seats_per_user
                })

        # Start all threads simultaneously
        for i, user in enumerate(users):
            thread = threading.Thread(target=book_seats_for_user, args=(user, i))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        return results

    def _display_results(self, results, schedule, seats_per_user):
        """Display the results of concurrent booking test"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('CONCURRENT BOOKING TEST RESULTS')
        self.stdout.write('='*60)
        
        successful_bookings = [r for r in results if r['success']]
        failed_bookings = [r for r in results if not r['success']]
        
        self.stdout.write(f'\nTotal users: {len(results)}')
        self.stdout.write(f'Successful bookings: {len(successful_bookings)}')
        self.stdout.write(f'Failed bookings: {len(failed_bookings)}')
        
        if successful_bookings:
            self.stdout.write('\nSuccessful Bookings:')
            for result in successful_bookings:
                self.stdout.write(
                    f"  ✓ {result['user']}: Seats {result['seats_booked']} "
                    f"(Booking ID: {result['booking_id']}, Time: {result['time_taken']:.3f}s)"
                )
        
        if failed_bookings:
            self.stdout.write('\nFailed Bookings:')
            for result in failed_bookings:
                self.stdout.write(f"  ✗ {result['user']}: {result['error']}")
        
        # Check final seat availability
        final_seats = SeatBookingService.get_available_seats(schedule.id)
        self.stdout.write(f'\nFinal available seats: {len(final_seats["available_seats"])}')
        
        # Verify no double-booking occurred
        all_booked_seats = set()
        for result in successful_bookings:
            if 'seats_booked' in result:
                all_booked_seats.update(result['seats_booked'])
        
        if seats_per_user > 0 and len(all_booked_seats) == len([r for r in results if r['success']]) * seats_per_user:
            self.stdout.write(self.style.SUCCESS('\n✓ SUCCESS: No double-booking detected!'))
        else:
            self.stdout.write(self.style.ERROR('\n✗ ERROR: Potential double-booking detected!'))

    def _cleanup_test_data(self, users, schedule):
        """Clean up test bookings and users"""
        self.stdout.write('\nCleaning up test data...')
        
        # Delete test bookings
        from ticket.models import Booking
        test_bookings = Booking.objects.filter(
            user__in=users,
            schedule=schedule
        )
        deleted_count = test_bookings.count()
        test_bookings.delete()
        
        self.stdout.write(f'Deleted {deleted_count} test bookings')
        
        # Delete test users
        for user in users:
            if user.username.startswith('test_user_'):
                user.delete()
                self.stdout.write(f'Deleted test user: {user.username}')
        
        self.stdout.write('Cleanup completed!') 