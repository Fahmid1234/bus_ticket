from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from .models import Bus, Route, Schedule, User, Booking, Ticket, TemporarySeatSelection
from .serializers import BusSerializer, RouteSerializer, ScheduleSerializer, UserSerializer, BookingSerializer, TicketSerializer, TemporarySeatSelectionSerializer
from .services import SeatBookingService

class BusViewSet(viewsets.ModelViewSet):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer

class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def seat_availability(self, request, pk=None):
        """Get real-time seat availability for a specific schedule"""
        try:
            seat_info = SeatBookingService.get_available_seats(pk)
            return Response({
                'schedule_id': pk,
                'available_seats': seat_info['available_seats'],
                'booked_seats': seat_info['booked_seats'],
                'total_seats': seat_info['total_seats'],
                'available_count': seat_info['available_count']
            })
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def seat_status(self, request, pk=None):
        """Get comprehensive seat status including temporary selections"""
        try:
            seat_status = SeatBookingService.get_seat_status(pk)
            return Response({
                'schedule_id': pk,
                'booked_seats': seat_status['booked_seats'],
                'temporary_selections': seat_status['temporary_selections'],
                'available_seats': seat_status['available_seats'],
                'total_seats': seat_status['total_seats'],
                'available_count': seat_status['available_count'],
                'booked_count': seat_status['booked_count'],
                'temporary_count': seat_status['temporary_count']
            })
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def check_seats(self, request, pk=None):
        """Check if specific seats are available for booking"""
        try:
            seat_numbers = request.data.get('seat_numbers', [])
            if not seat_numbers:
                return Response(
                    {'error': 'seat_numbers is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            seat_info = SeatBookingService.check_seat_availability(pk, seat_numbers)
            return Response({
                'schedule_id': pk,
                'requested_seats': seat_numbers,
                'available_seats': seat_info['available'],
                'unavailable_seats': seat_info['unavailable'],
                'all_available': seat_info['all_available']
            })
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class TemporarySeatSelectionViewSet(viewsets.ModelViewSet):
    queryset = TemporarySeatSelection.objects.all()
    serializer_class = TemporarySeatSelectionSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def select_seat(self, request):
        """Temporarily select a seat"""
        try:
            schedule_id = request.data.get('schedule_id')
            seat_number = request.data.get('seat_number')
            
            if not all([schedule_id, seat_number]):
                return Response(
                    {'error': 'schedule_id and seat_number are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            selection = SeatBookingService.select_seat_temporarily(
                schedule_id=schedule_id,
                user=request.user,
                seat_number=seat_number
            )
            
            return Response({
                'success': True,
                'selection_id': selection.id,
                'message': f'Seat {seat_number} temporarily selected'
            })
            
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def deselect_seat(self, request):
        """Remove temporary seat selection"""
        try:
            schedule_id = request.data.get('schedule_id')
            seat_number = request.data.get('seat_number')
            
            if not all([schedule_id, seat_number]):
                return Response(
                    {'error': 'schedule_id and seat_number are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            success = SeatBookingService.deselect_seat_temporarily(
                schedule_id=schedule_id,
                user=request.user,
                seat_number=seat_number
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': f'Seat {seat_number} deselected'
                })
            else:
                return Response({
                    'success': False,
                    'message': 'No temporary selection found for this seat'
                })
            
        except Exception as e:
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def book_seats(self, request):
        """Book seats with transaction-based locking"""
        try:
            schedule_id = request.data.get('schedule_id')
            passenger_name = request.data.get('passenger_name')
            passenger_email = request.data.get('passenger_email')
            passenger_phone = request.data.get('passenger_phone')
            seat_numbers = request.data.get('seat_numbers', [])
            
            if not all([schedule_id, passenger_name, passenger_email, passenger_phone, seat_numbers]):
                return Response(
                    {'error': 'All fields are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Use the service to book seats with proper locking
            booking_result = SeatBookingService.book_seats_with_lock(
                schedule_id=schedule_id,
                user=request.user,
                passenger_name=passenger_name,
                passenger_email=passenger_email,
                passenger_phone=passenger_phone,
                seat_numbers=seat_numbers
            )
            
            return Response({
                'success': True,
                'booking_id': booking_result['booking'].id,
                'total_amount': float(booking_result['total_amount']),
                'message': 'Seats booked successfully'
            })
            
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def cancel_booking(self, request, pk=None):
        """Cancel a booking and release seats"""
        try:
            success = SeatBookingService.cancel_booking(pk, request.user)
            return Response({
                'success': True,
                'message': 'Booking cancelled successfully'
            })
        except ValidationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer 