from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Schedule, Booking, Ticket, Bus, TemporarySeatSelection
from django.db.models import F, Q, Sum
import logging

logger = logging.getLogger(__name__)

class SeatBookingService:
    """
    Service class to handle seat booking with transaction-based locking
    to prevent race conditions and double-booking.
    """
    
    @staticmethod
    def cleanup_expired_selections():
        """
        Clean up expired temporary seat selections.
        This should be called periodically or before seat availability checks.
        """
        try:
            expired_count = TemporarySeatSelection.objects.filter(
                expires_at__lt=timezone.now()
            ).delete()[0]
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired temporary seat selections")
            return expired_count
        except Exception as e:
            logger.error(f"Error cleaning up expired selections: {str(e)}")
            return 0
    
    @staticmethod
    def select_seat_temporarily(schedule_id, user, seat_number):
        """
        Temporarily select a seat for a user. This seat will be visible to other users
        but will expire after 5 minutes if not confirmed.
        """
        try:
            with transaction.atomic():
                # Clean up expired selections first
                SeatBookingService.cleanup_expired_selections()
                
                # Lock the schedule to prevent concurrent modifications
                schedule = Schedule.objects.select_for_update().get(id=schedule_id)
                
                # Check if schedule has departed
                if schedule.departure_time <= timezone.now():
                    raise ValidationError('Cannot select seats for a schedule that has already departed')
                
                # Check if seat is already booked
                booked_seats = set(Ticket.objects.filter(
                    booking__schedule=schedule
                ).values_list('seat_number', flat=True))
                
                if seat_number in booked_seats:
                    raise ValidationError(f'Seat {seat_number} is already booked')
                
                # Check if seat is already temporarily selected
                existing_selection = TemporarySeatSelection.objects.filter(
                    schedule=schedule,
                    seat_number=seat_number
                ).first()
                
                if existing_selection:
                    if existing_selection.user == user:
                        # User is re-selecting the same seat, extend expiration
                        existing_selection.expires_at = timezone.now() + timezone.timedelta(minutes=5)
                        existing_selection.save()
                        return existing_selection
                    else:
                        # Another user has this seat temporarily selected
                        raise ValidationError(f'Seat {seat_number} is temporarily selected by another user')
                
                # Create new temporary selection
                selection = TemporarySeatSelection.objects.create(
                    schedule=schedule,
                    user=user,
                    seat_number=seat_number
                )
                
                return selection
                
        except Schedule.DoesNotExist:
            raise ValidationError('Schedule not found')
        except Exception as e:
            logger.error(f'Error selecting seat temporarily: {str(e)}')
            raise ValidationError(f'Failed to select seat: {str(e)}')
    
    @staticmethod
    def deselect_seat_temporarily(schedule_id, user, seat_number):
        """
        Remove a temporary seat selection for a user.
        """
        try:
            selection = TemporarySeatSelection.objects.filter(
                schedule_id=schedule_id,
                user=user,
                seat_number=seat_number
            ).first()
            
            if selection:
                selection.delete()
                return True
            return False
            
        except Exception as e:
            logger.error(f'Error deselecting seat: {str(e)}')
            return False
    
    @staticmethod
    def get_seat_status(schedule_id):
        """
        Get comprehensive seat status for a schedule including:
        - Booked seats (confirmed bookings)
        - Temporarily selected seats (pending selections)
        - Available seats
        """
        try:
            # Clean up expired selections first
            SeatBookingService.cleanup_expired_selections()
            
            schedule = Schedule.objects.get(id=schedule_id)
            
            # Get booked seats (confirmed)
            booked_seats = set(Ticket.objects.filter(
                booking__schedule=schedule
            ).values_list('seat_number', flat=True))
            
            # Get temporarily selected seats
            temp_selections = TemporarySeatSelection.objects.filter(
                schedule=schedule
            ).select_related('user')
            
            temp_seats = {}
            for selection in temp_selections:
                temp_seats[selection.seat_number] = {
                    'user_id': selection.user.id,
                    'username': selection.user.username,
                    'selected_at': selection.selected_at,
                    'expires_at': selection.expires_at
                }
            
            # Calculate available seats
            all_seats = set(range(1, schedule.bus.capacity + 1))
            available_seats = sorted(all_seats - booked_seats - set(temp_seats.keys()))
            
            return {
                'schedule': schedule,
                'booked_seats': sorted(booked_seats),
                'temporary_selections': temp_seats,
                'available_seats': available_seats,
                'total_seats': schedule.bus.capacity,
                'available_count': len(available_seats),
                'booked_count': len(booked_seats),
                'temporary_count': len(temp_seats)
            }
            
        except Schedule.DoesNotExist:
            raise ValidationError('Schedule not found')
        except Exception as e:
            logger.error(f'Error getting seat status: {str(e)}')
            raise ValidationError(f'Failed to get seat status: {str(e)}')
    
    @staticmethod
    def check_seat_availability(schedule_id, seat_numbers):
        """
        Check if seats are available for a given schedule.
        This is a read-only check that doesn't lock seats.
        """
        try:
            # Clean up expired selections first
            SeatBookingService.cleanup_expired_selections()
            
            schedule = Schedule.objects.select_for_update().get(id=schedule_id)
            
            # Get currently booked seats for this schedule
            booked_seats = set(Ticket.objects.filter(
                booking__schedule=schedule
            ).values_list('seat_number', flat=True))
            
            # Get temporarily selected seats
            temp_seats = set(TemporarySeatSelection.objects.filter(
                schedule=schedule
            ).values_list('seat_number', flat=True))
            
            # Check if requested seats are available
            available_seats = []
            unavailable_seats = []
            
            for seat in seat_numbers:
                if seat in booked_seats or seat in temp_seats:
                    unavailable_seats.append(seat)
                else:
                    available_seats.append(seat)
            
            return {
                'available': available_seats,
                'unavailable': unavailable_seats,
                'all_available': len(unavailable_seats) == 0,
                'schedule': schedule
            }
        except Schedule.DoesNotExist:
            raise ValidationError('Schedule not found')
    
    @staticmethod
    def book_seats_with_lock(schedule_id, user, passenger_name, passenger_email, 
                           passenger_phone, seat_numbers, max_seats_per_user=4):
        """
        Book seats with database-level locking to prevent race conditions.
        Uses SELECT FOR UPDATE to lock the schedule and prevent concurrent modifications.
        """
        try:
            with transaction.atomic():
                # Clean up expired selections first
                SeatBookingService.cleanup_expired_selections()
                
                # Lock the schedule to prevent concurrent modifications
                schedule = Schedule.objects.select_for_update().get(id=schedule_id)
                
                # Check if schedule has departed
                if schedule.departure_time <= timezone.now():
                    raise ValidationError('Cannot book seats for a schedule that has already departed')
                
                # Check user's existing bookings for this schedule
                user_bookings = Booking.objects.filter(
                    user=user,
                    schedule=schedule
                )
                user_total_seats = user_bookings.aggregate(
                    total=Sum('seats_booked')
                )['total'] or 0
                
                # Check if user can book more seats
                if user_total_seats + len(seat_numbers) > max_seats_per_user:
                    raise ValidationError(
                        f'You can only book up to {max_seats_per_user} seats for the same bus schedule. '
                        f'You have already booked {user_total_seats} seats.'
                    )
                
                # Double-check seat availability with lock
                booked_seats = set(Ticket.objects.filter(
                    booking__schedule=schedule
                ).values_list('seat_number', flat=True))
                
                # Check temporarily selected seats
                temp_seats = set(TemporarySeatSelection.objects.filter(
                    schedule=schedule
                ).values_list('seat_number', flat=True))
                
                # Check if any requested seats are already booked or temporarily selected
                unavailable_seats = [seat for seat in seat_numbers if seat in booked_seats or seat in temp_seats]
                if unavailable_seats:
                    raise ValidationError(
                        f'Seats {unavailable_seats} are no longer available. '
                        'Please select different seats.'
                    )
                
                # Validate seat numbers are within bus capacity
                if any(seat < 1 or seat > schedule.bus.capacity for seat in seat_numbers):
                    raise ValidationError(
                        f'Invalid seat numbers. Bus capacity is {schedule.bus.capacity}.'
                    )
                
                # Create the booking
                booking = Booking.objects.create(
                    schedule=schedule,
                    user=user,
                    passenger_name=passenger_name,
                    passenger_email=passenger_email,
                    passenger_phone=passenger_phone,
                    seats_booked=len(seat_numbers)
                )
                
                # Create tickets for each seat
                tickets = []
                for seat_number in seat_numbers:
                    ticket = Ticket.objects.create(
                        booking=booking,
                        seat_number=seat_number
                    )
                    tickets.append(ticket)
                
                # Remove any temporary selections for these seats by this user
                TemporarySeatSelection.objects.filter(
                    schedule=schedule,
                    user=user,
                    seat_number__in=seat_numbers
                ).delete()
                
                # Calculate total amount
                total_amount = schedule.fare * len(seat_numbers)
                
                return {
                    'booking': booking,
                    'tickets': tickets,
                    'total_amount': total_amount
                }
                
        except Exception as e:
            logger.error(f'Error booking seats: {str(e)}')
            raise ValidationError(f'Failed to book seats: {str(e)}')
    
    @staticmethod
    def get_available_seats(schedule_id):
        """
        Get available seats for a schedule with proper locking.
        """
        try:
            with transaction.atomic():
                # Clean up expired selections first
                SeatBookingService.cleanup_expired_selections()
                
                schedule = Schedule.objects.select_for_update().get(id=schedule_id)
                
                # Get booked seats
                booked_seats = set(Ticket.objects.filter(
                    booking__schedule=schedule
                ).values_list('seat_number', flat=True))
                
                # Get temporarily selected seats
                temp_seats = set(TemporarySeatSelection.objects.filter(
                    schedule=schedule
                ).values_list('seat_number', flat=True))
                
                # Calculate available seats
                all_seats = set(range(1, schedule.bus.capacity + 1))
                available_seats = sorted(all_seats - booked_seats - temp_seats)
                
                return {
                    'schedule': schedule,
                    'available_seats': available_seats,
                    'booked_seats': sorted(booked_seats),
                    'temporary_seats': sorted(temp_seats),
                    'total_seats': schedule.bus.capacity,
                    'available_count': len(available_seats)
                }
        except Schedule.DoesNotExist:
            raise ValidationError('Schedule not found')
    
    @staticmethod
    def cancel_booking(booking_id, user):
        """
        Cancel a booking and release seats.
        """
        try:
            with transaction.atomic():
                booking = Booking.objects.select_for_update().get(id=booking_id, user=user)
                
                if not booking.is_confirmed:
                    # Delete the booking and associated tickets
                    booking.delete()
                    return True
                else:
                    raise ValidationError('Cannot cancel a confirmed booking')
                    
        except Booking.DoesNotExist:
            raise ValidationError('Booking not found')
        except Exception as e:
            logger.error(f'Error cancelling booking: {str(e)}')
            raise ValidationError(f'Failed to cancel booking: {str(e)}')
    
    @staticmethod
    def get_user_bookings(user, schedule_id=None):
        """
        Get all bookings for a user, optionally filtered by schedule.
        """
        queryset = Booking.objects.filter(user=user)
        if schedule_id:
            queryset = queryset.filter(schedule_id=schedule_id)
        return queryset.order_by('-booking_time') 