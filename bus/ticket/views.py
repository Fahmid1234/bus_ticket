from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from .models import Schedule, Booking, Ticket, Route
from django.urls import reverse
from django.utils import timezone
from django.db.models import F, Count, Q, Sum
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse, FileResponse
from .utils import initiate_payment, verify_payment
from django.contrib import messages
from decimal import Decimal
import logging
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, ResendActivationEmailForm, ProfileUpdateForm
from django.core.exceptions import ValidationError
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import qrcode
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import Color, red
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .services import SeatBookingService

logger = logging.getLogger(__name__)
User = get_user_model()
# Create your views here.
def home(request):
    return render(request, 'index.html')

def schedule(request):
    # Get current time
    current_time = timezone.now()
    
    # Filter out schedules that have already departed
    schedules = Schedule.objects.filter(departure_time__gt=current_time)
    
    origin = request.GET.get('origin', '').strip()
    destination = request.GET.get('destination', '').strip()
    date = request.GET.get('date', '').strip()

    if origin:
        schedules = schedules.filter(route__origin__icontains=origin)
    if destination:
        schedules = schedules.filter(route__destination__icontains=destination)
    if date:
        try:
            date_obj = timezone.datetime.strptime(date, '%Y-%m-%d').date()
            schedules = schedules.filter(departure_time__date=date_obj)
        except ValueError:
            pass

    # Get all schedules with their related bus and route info
    schedules = schedules.select_related('bus', 'route').order_by('departure_time')
    
    # Calculate available seats for each schedule
    for schedule in schedules:
        try:
            # Use the service to get seat information
            seat_info = SeatBookingService.get_available_seats(schedule.id)
            schedule.available_seats = seat_info['available_count']
            schedule.available_seat_numbers = seat_info['available_seats']
            
            # Check if schedule is departing soon (within 1 hour)
            time_until_departure = schedule.departure_time - current_time
            schedule.is_departing_soon = time_until_departure.total_seconds() <= 3600 and time_until_departure.total_seconds() > 0
        except ValidationError:
            # Fallback to old method if service fails
            booked_seats = Ticket.objects.filter(booking__schedule=schedule).count()
            schedule.available_seats = schedule.bus.capacity - booked_seats
            
            booked_seat_numbers = set(Ticket.objects.filter(
                booking__schedule=schedule
            ).values_list('seat_number', flat=True))
            
            all_seat_numbers = set(range(1, schedule.bus.capacity + 1))
            schedule.available_seat_numbers = sorted(all_seat_numbers - booked_seat_numbers)
            
            time_until_departure = schedule.departure_time - current_time
            schedule.is_departing_soon = time_until_departure.total_seconds() <= 3600 and time_until_departure.total_seconds() > 0
    
    # Pagination
    paginator = Paginator(schedules, 20)  # Show 20 schedules per page
    page = request.GET.get('page')
    
    try:
        schedules_page = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        schedules_page = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        schedules_page = paginator.page(paginator.num_pages)
    
    return render(request, 'schedule.html', {
        'schedules': schedules_page,
        'origin': origin,
        'destination': destination,
        'date': date
    })

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            # Send activation email
            current_site = get_current_site(request)
            subject = 'Activate Your Account'
            message = render_to_string('registration/account_activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
            messages.success(request, 'Registration successful! Please check your email to activate your account.')
            return redirect('check_email')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def booking(request):
    schedule_id = request.GET.get('schedule_id') or request.POST.get('schedule_id')
    schedule = get_object_or_404(Schedule, id=schedule_id) if schedule_id else None
    
    seat_range = []
    booked_seats = []
    available_seats_count = 0
    user_maxed_out = False
    error = None
    
    if schedule:
        try:
            # Use the service to get seat information with proper locking
            seat_info = SeatBookingService.get_available_seats(schedule.id)
            seat_range = range(1, schedule.bus.capacity + 1)
            booked_seats = seat_info['booked_seats']
            available_seats_count = seat_info['available_count']
            
            # Get user's existing bookings for this schedule
            user_bookings = SeatBookingService.get_user_bookings(request.user, schedule.id)
            user_total_seats = sum(booking.seats_booked for booking in user_bookings)
            remaining_seats = 4 - user_total_seats
            
            if remaining_seats <= 0:
                user_maxed_out = True
                
        except ValidationError as e:
            error = str(e)
            schedule = None

    if request.method == 'POST' and schedule and not user_maxed_out:
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        seats_str = request.POST.getlist('seats')
        seats = [int(s) for s in seats_str]

        if not name or not email or not phone or not seats:
            error = 'Please fill all fields and select at least one seat.'
        elif not phone.isdigit() or len(phone) != 11:
            error = 'Please enter a valid 11-digit phone number.'
        elif len(seats) > remaining_seats:
            error = f'You can only book {remaining_seats} more seats for this bus.'
        else:
            try:
                # Use the service to book seats with transaction-based locking
                booking_result = SeatBookingService.book_seats_with_lock(
                    schedule_id=schedule.id,
                    user=request.user,
                    passenger_name=name,
                    passenger_email=email,
                    passenger_phone=phone,
                    seat_numbers=seats
                )
                
                # Redirect to payment page with booking ID in URL
                return redirect('payment', booking_id=booking_result['booking'].id)
                
            except ValidationError as e:
                error = str(e)

    return render(request, 'booking.html', {
        'schedule': schedule,
        'seat_range': seat_range,
        'booked_seats': booked_seats,
        'available_seats_count': available_seats_count,
        'error': error,
        'user_maxed_out': user_maxed_out
    })

def payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    tickets = Ticket.objects.filter(booking=booking)
    
    # Calculate total amount
    total_amount = booking.seats_booked * booking.schedule.fare
    
    return render(request, 'payment.html', {
        'booking': booking,
        'tickets': tickets,
        'total_amount': total_amount
    })

@csrf_exempt
def initiate_payment_view(request):
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        if not booking_id:
            messages.error(request, 'No booking ID provided')
            return redirect('home')
            
        try:
            booking = get_object_or_404(Booking, id=booking_id)
            
            # Check if booking is already paid
            if booking.is_confirmed:
                messages.warning(request, 'This booking is already paid')
                return redirect('confirm_booking', booking_id=booking_id)
            
            # Initiate payment
            logger.info(f"Initiating payment for booking {booking_id}")
            payment_data = initiate_payment(booking)
            
            if payment_data.get('status') == 'SUCCESS':
                gateway_url = payment_data.get('GatewayPageURL')
                logger.info(f"Payment initiation successful for booking {booking_id}. Redirecting to gateway.")
                return redirect(gateway_url)
            else:
                error_message = payment_data.get('message', 'Payment initiation failed')
                logger.error(f"Payment initiation failed for booking {booking_id}: {error_message}")
                messages.error(request, f"Payment initiation failed: {error_message}")
                return redirect('payment', booking_id=booking_id)
                
        except Exception as e:
            logger.error(f"Error in payment initiation view: {str(e)}")
            messages.error(request, 'An error occurred while processing your payment')
            return redirect('payment', booking_id=booking_id)
    
    messages.error(request, 'Invalid request method')
    return redirect('home')

@csrf_exempt
def payment_success(request):
    if request.method == 'POST':
        payment_data = request.POST
        logger.info(f"Received success callback: {payment_data}")
        is_valid, booking_id = verify_payment(payment_data)
        if is_valid and booking_id:
            try:
                booking = get_object_or_404(Booking, id=booking_id)
                booking.is_confirmed = True
                booking.save()
                logger.info(f"Payment confirmed for booking {booking_id}")
                messages.success(request, 'Payment successful! Your booking is confirmed.')
                # Pass just_paid flag to invoice page
                return redirect(f'/confirm-booking/?booking_id={booking_id}&just_paid=1')
            except Exception as e:
                logger.error(f"Error updating booking {booking_id}: {str(e)}")
                messages.error(request, 'Error confirming your booking')
        else:
            logger.warning(f"Invalid payment verification for data: {payment_data}")
            messages.error(request, 'Payment verification failed')
    return redirect('home')

@csrf_exempt
def payment_fail(request):
    booking_id = request.POST.get('booking_id') or request.GET.get('booking_id')
    if request.method == 'POST':
        logger.warning(f"Payment failed: {request.POST}")
        # Show payment failed page with retry option
        return render(request, 'payment.html', {
            'payment_failed': True,
            'booking_id': booking_id
        })
    # If not POST, just redirect home
    return redirect('home')

@csrf_exempt
def payment_cancel(request):
    if request.method == 'POST':
        logger.info(f"Payment cancelled: {request.POST}")
        messages.warning(request, 'Payment was cancelled.')
    return redirect('home')

@csrf_exempt
def payment_ipn(request):
    if request.method == 'POST':
        payment_data = request.POST
        logger.info(f"Received IPN: {payment_data}")
        
        is_valid, booking_id = verify_payment(payment_data)
        
        if is_valid and booking_id:
            try:
                booking = get_object_or_404(Booking, id=booking_id)
                booking.is_confirmed = True
                booking.save()
                logger.info(f"IPN: Payment confirmed for booking {booking_id}")
            except Exception as e:
                logger.error(f"IPN: Error updating booking {booking_id}: {str(e)}")
    
    return HttpResponse(status=200)

def contact(request):
    return render(request, 'contact.html')

def confirm_booking(request):
    booking_id = request.GET.get('booking_id')
    just_paid = request.GET.get('just_paid') == '1'
    booking = get_object_or_404(Booking, id=booking_id)
    tickets = Ticket.objects.filter(booking=booking)
    return render(request, 'confirm-booking.html', {
        'booking': booking,
        'tickets': tickets,
        'just_paid': just_paid
    })

def logout_view(request):
    logout(request)
    return redirect('home')

def city_suggestions(request):
    """
    Returns a JSON list of unique city names (origins or destinations) matching the query.
    Query params:
      - q: the search string
      - type: 'origin' or 'destination'
    """
    q = request.GET.get('q', '').strip()
    field_type = request.GET.get('type', 'origin')
    if field_type not in ['origin', 'destination']:
        field_type = 'origin'
    
    if field_type == 'origin':
        cities = Route.objects.values_list('origin', flat=True)
    else:
        cities = Route.objects.values_list('destination', flat=True)
    
    # Remove duplicates and filter by query
    unique_cities = sorted(set(cities))
    if q:
        unique_cities = [city for city in unique_cities if q.lower() in city.lower()]
    return JsonResponse({'results': unique_cities[:10]})

@login_required
def download_invoice(request):
    from reportlab.lib.units import mm
    from reportlab.lib.colors import Color, red
    from reportlab.pdfgen import canvas
    import io

    def seat_label(seat_number, seats_per_row=4):
        # Convert seat number (1-based) to label like A1, A2, B1, etc.
        row = (seat_number - 1) // seats_per_row
        col = (seat_number - 1) % seats_per_row + 1
        return f"{chr(65 + row)}{col}"

    booking_id = request.GET.get('booking_id')
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    tickets = Ticket.objects.filter(booking=booking)

    buffer = io.BytesIO()
    width, height = 900, 375  # Custom size for visual match (in points)
    p = canvas.Canvas(buffer, pagesize=(width, height))

    # Colors
    blue = Color(0.2, 0.4, 1, 1)
    black = Color(0, 0, 0, 1)

    # Outer border
    border_margin = 15
    p.setStrokeColor(blue)
    p.setLineWidth(3)
    p.rect(border_margin, border_margin, width - 2*border_margin, height - 2*border_margin, stroke=1, fill=0)

    # Company name (top-left)
    p.setFont('Helvetica-Bold', 38)
    p.setFillColor(blue)
    p.drawString(border_margin + 30, height - border_margin - 50, 'BusTicketPro')

    # PAID stamp (top-right, angled)
    p.saveState()
    p.translate(width - 220, height - 80)
    p.rotate(15)
    p.setFont('Helvetica-Bold', 38)
    p.setFillColor(red)
    p.drawString(0, 0, "PAID")
    p.restoreState()

    # Route: Origin (left), Arrow, Destination (right)
    origin = booking.schedule.route.origin
    destination = booking.schedule.route.destination
    y_route = height - border_margin - 110
    p.setFont('Helvetica-Bold', 36)
    p.setFillColor(black)
    p.drawString(border_margin + 20, y_route, origin)
    # Arrow line
    arrow_start_x = border_margin + 210
    arrow_end_x = width - border_margin - 210
    arrow_y = y_route + 18
    p.setLineWidth(4)
    p.setStrokeColor(black)
    p.line(arrow_start_x, arrow_y, arrow_end_x, arrow_y)
    # Arrowhead
    p.line(arrow_end_x, arrow_y, arrow_end_x - 18, arrow_y + 10)
    p.line(arrow_end_x, arrow_y, arrow_end_x - 18, arrow_y - 10)
    # Destination (right)
    p.setFont('Helvetica-Bold', 36)
    p.drawRightString(width - border_margin - 20, y_route, destination)

    # Left column info
    left_x = border_margin + 20
    y = y_route - 50
    line_gap = 38
    p.setFont('Helvetica-Bold', 22)
    p.drawString(left_x, y, "Date:")
    p.setFont('Helvetica', 22)
    p.drawString(left_x + 90, y, booking.schedule.departure_time.strftime('%Y-%m-%d'))

    y -= line_gap
    p.setFont('Helvetica-Bold', 22)
    p.drawString(left_x, y, "Bus:")
    p.setFont('Helvetica', 22)
    p.drawString(left_x + 90, y, f"{booking.schedule.bus.name} ({booking.schedule.bus.bus_type})")

    y -= line_gap
    p.setFont('Helvetica-Bold', 22)
    p.drawString(left_x, y, "Passenger:")
    p.setFont('Helvetica', 22)
    p.drawString(left_x + 130, y, booking.passenger_name)

    y -= line_gap
    p.setFont('Helvetica-Bold', 22)
    p.drawString(left_x, y, "Email:")
    p.setFont('Helvetica', 22)
    p.drawString(left_x + 90, y, booking.passenger_email)

    # Right column info
    right_x = width - border_margin - 320
    y = y_route - 50
    p.setFont('Helvetica-Bold', 22)
    p.drawString(right_x, y, "Time:")
    p.setFont('Helvetica', 22)
    p.drawString(right_x + 100, y, booking.schedule.departure_time.strftime('%H:%M'))

    y -= line_gap
    p.setFont('Helvetica-Bold', 22)
    p.drawString(right_x, y, "Seats:")
    seat_str = ", ".join(seat_label(t.seat_number) for t in tickets)
    p.setFont('Helvetica', 22)
    p.drawString(right_x + 110, y, seat_str)

    y -= line_gap
    p.setFont('Helvetica-Bold', 22)
    p.drawString(right_x, y, "Fare:")
    p.setFont('Helvetica', 22)
    p.drawString(right_x + 100, y, f"{booking.seats_booked * booking.schedule.fare:.2f} TK")

    y -= line_gap
    p.setFont('Helvetica-Bold', 22)
    p.drawString(right_x, y, "Booked:")
    p.setFont('Helvetica', 22)
    p.drawString(right_x + 130, y, booking.booking_time.strftime('%Y-%m-%d %H:%M'))

    # Footer (bottom-right)
    p.setFont('Helvetica-Oblique', 18)
    p.setFillColor(blue)
    p.drawRightString(width - border_margin - 10, border_margin + 18, "Thank you for booking with BusTicketPro!")

    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'BusTicketPro_Ticket_{booking.id}.pdf')

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account has been activated! You can now log in.')
        return redirect('login')
    else:
        return HttpResponse('Activation link is invalid!', status=400)

@login_required
def profile(request):
    user = request.user
    # Profile update logic
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=user)
    # Trip logic
    now = timezone.now()
    bookings = Booking.objects.filter(user=user).select_related('schedule__route', 'schedule__bus').order_by('-schedule__departure_time')
    upcoming_trips = []
    past_trips = []
    for booking in bookings:
        if booking.schedule.departure_time >= now:
            upcoming_trips.append(booking)
        else:
            past_trips.append(booking)
    # Tickets for each booking
    tickets_by_booking = {b.id: list(Ticket.objects.filter(booking=b)) for b in bookings}
    return render(request, 'registration/profile.html', {
        'user': user,
        'form': form,
        'upcoming_trips': upcoming_trips,
        'past_trips': past_trips,
        'tickets_by_booking': tickets_by_booking,
    })

def check_email(request):
    return render(request, 'registration/check_email.html')

def resend_activation_email(request):
    message = None
    if request.method == 'POST':
        form = ResendActivationEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                if not user.is_active:
                    current_site = get_current_site(request)
                    subject = 'Activate Your Account'
                    message = render_to_string('registration/account_activation_email.html', {
                        'user': user,
                        'domain': current_site.domain,
                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                        'token': default_token_generator.make_token(user),
                    })
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
                    message = 'A new activation email has been sent. Please check your inbox.'
                else:
                    message = 'This account is already active. You can log in.'
            except User.DoesNotExist:
                message = 'No account found with that email.'
    else:
        form = ResendActivationEmailForm()
    return render(request, 'registration/resend_activation_email.html', {'form': form, 'message': message})
