from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from ticket.models import Bus, Route, Schedule
import random

class Command(BaseCommand):
    help = 'Create exactly 1500 schedules in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing schedules before creating new ones',
        )

    def handle(self, *args, **options):
        clear_existing = options.get('clear_existing', False)
        
        if clear_existing:
            self.stdout.write('Clearing existing schedules...')
            Schedule.objects.all().delete()
            self.stdout.write('Existing schedules cleared.')
        
        # Check if we have buses and routes
        bus_count = Bus.objects.count()
        route_count = Route.objects.count()
        
        if bus_count == 0:
            self.stdout.write(
                self.style.ERROR('No buses found. Please run populate_bus_data first.')
            )
            return
        
        if route_count == 0:
            self.stdout.write(
                self.style.ERROR('No routes found. Please run populate_bus_data first.')
            )
            return
        
        self.stdout.write(f'Found {bus_count} buses and {route_count} routes.')
        self.stdout.write('Creating 1500 schedules...')
        
        # Get all buses and routes
        buses = list(Bus.objects.all())
        routes = list(Route.objects.all())
        
        # Calculate schedules per route to distribute evenly
        schedules_per_route = 1500 // route_count
        remaining_schedules = 1500 % route_count
        
        # Start time (tomorrow at 6 AM)
        base_time = (timezone.now() + timedelta(days=1)).replace(
            hour=6, minute=0, second=0, microsecond=0
        )
        
        total_created = 0
        
        for i, route in enumerate(routes):
            # Calculate how many schedules for this route
            if i < remaining_schedules:
                route_schedule_count = schedules_per_route + 1
            else:
                route_schedule_count = schedules_per_route
            
            # Generate departure times for this route
            departure_times = self._generate_departure_times(route.distance_km, route_schedule_count)
            
            for departure_time in departure_times:
                # Select random bus
                bus = random.choice(buses)
                
                # Calculate arrival time based on distance
                travel_hours = self._calculate_travel_time(route.distance_km)
                arrival_time = departure_time + timedelta(hours=travel_hours)
                
                # Calculate fare
                fare = self._calculate_fare(route.distance_km, bus.bus_type)
                
                # Create schedule
                schedule = Schedule.objects.create(
                    bus=bus,
                    route=route,
                    departure_time=departure_time,
                    arrival_time=arrival_time,
                    fare=fare
                )
                
                total_created += 1
                
                if total_created % 100 == 0:
                    self.stdout.write(f'Created {total_created} schedules...')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {total_created} schedules!'
            )
        )
        
        # Show summary
        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'- Total schedules: {Schedule.objects.count()}')
        self.stdout.write(f'- Routes covered: {route_count}')
        self.stdout.write(f'- Buses used: {bus_count}')
    
    def _generate_departure_times(self, distance, count):
        """Generate departure times for a route based on distance and count needed"""
        times = []
        
        # Determine time range based on distance
        if distance <= 100:  # Local routes
            start_hour, end_hour = 6, 22
        elif distance <= 200:  # Medium routes
            start_hour, end_hour = 6, 20
        elif distance <= 300:  # Long routes
            start_hour, end_hour = 6, 18
        else:  # Very long routes
            start_hour, end_hour = 6, 16
        
        # Generate times over 7 days
        for day in range(7):
            for hour in range(start_hour, end_hour + 1):
                for minute in [0, 30]:  # Every 30 minutes
                    time = (timezone.now() + timedelta(days=day+1)).replace(
                        hour=hour, minute=minute, second=0, microsecond=0
                    )
                    times.append(time)
        
        # If we have more times than needed, randomly select
        if len(times) > count:
            times = random.sample(times, count)
        elif len(times) < count:
            # If we need more times, add some random times
            while len(times) < count:
                day = random.randint(1, 7)
                hour = random.randint(start_hour, end_hour)
                minute = random.choice([0, 15, 30, 45])
                time = (timezone.now() + timedelta(days=day)).replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
                if time not in times:
                    times.append(time)
        
        return times[:count]
    
    def _calculate_travel_time(self, distance):
        """Calculate travel time in hours based on distance"""
        if distance <= 100:
            avg_speed = 45  # Local roads
        elif distance <= 200:
            avg_speed = 55  # Mixed roads
        elif distance <= 300:
            avg_speed = 65  # Highways
        else:
            avg_speed = 70  # Express highways
        
        return distance / avg_speed
    
    def _calculate_fare(self, distance, bus_type):
        """Calculate realistic fare based on distance and bus type"""
        # Base fare rates per km
        base_rates = {
            'Economy Class': 1.8,
            'Business Class': 7.0,
            'Hino RN8': 4.0,
            'Hino RM2': 3.0,
            'Hyundai Universe': 5.0,
            'Hyundai County': 4.0,
            'Hino RK8': 5.0,
            'Hino RN8J': 4.0,
            'Hyundai Aero': 4.0,
            'Hino RM2J': 3.0,
        }
        
        base_rate = base_rates.get(bus_type, 2.5)
        base_fare = distance * base_rate
        
        # Add distance-based adjustments
        if distance > 300:
            base_fare *= 0.95
        elif distance > 200:
            base_fare *= 0.98
        
        # Minimum fare protection
        min_fares = {
            'Economy Class': 50,
            'Business Class': 300,
            'Hino RN8': 150,
            'Hino RM2': 100,
            'Hyundai Universe': 200,
            'Hyundai County': 150,
            'Hino RK8': 200,
            'Hino RN8J': 150,
            'Hyundai Aero': 150,
            'Hino RM2J': 100
        }
        
        min_fare = min_fares.get(bus_type, 80)
        final_fare = max(base_fare, min_fare)
        
        # Round to nearest 50 for prices above 200, nearest 10 for prices below 200
        if final_fare > 200:
            final_fare = round(final_fare / 50) * 50
        else:
            final_fare = round(final_fare / 10) * 10
        
        return max(final_fare, min_fare) 