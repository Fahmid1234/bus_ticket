from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone

# Create your models here.

class Bus(models.Model):
    name = models.CharField(max_length=100, default="")
    number_plate = models.CharField(max_length=20, unique=True)
    capacity = models.PositiveIntegerField()
    bus_type = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.number_plate}, {self.bus_type})"

class Route(models.Model):
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    distance_km = models.FloatField()

    def __str__(self):
        return f"{self.origin} to {self.destination}"

class Schedule(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    fare = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.bus} - {self.route} at {self.departure_time}"

class User(AbstractUser):
    phone = models.CharField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return self.username

class TemporarySeatSelection(models.Model):
    """
    Model to track temporary seat selections by users before they complete booking.
    This allows other users to see which seats are being selected in real-time.
    """
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='temporary_selections')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seat_number = models.PositiveIntegerField()
    selected_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        unique_together = ['schedule', 'seat_number']
        indexes = [
            models.Index(fields=['schedule', 'seat_number']),
            models.Index(fields=['expires_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Set expiration to 5 minutes from now
            self.expires_at = timezone.now() + timezone.timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if the temporary selection has expired"""
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"Temporary selection: Seat {self.seat_number} by {self.user.username} on {self.schedule}"

class Booking(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    passenger_name = models.CharField(max_length=100)
    passenger_email = models.EmailField()
    passenger_phone = models.CharField(max_length=15, null=True, blank=True)
    seats_booked = models.PositiveIntegerField()
    booking_time = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False)

    def clean(self):
        if self.user:
            # Check if user has already booked 4 tickets for this schedule
            user_bookings = Booking.objects.filter(
                user=self.user,
                schedule=self.schedule
            ).exclude(pk=self.pk)
            
            total_seats = sum(booking.seats_booked for booking in user_bookings)
            if total_seats + self.seats_booked > 4:
                raise ValidationError('You can only book up to 4 seats for the same bus schedule.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking for {self.passenger_name} on {self.schedule}"

class Ticket(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    seat_number = models.PositiveIntegerField()
    issued_at = models.DateTimeField(auto_now_add=True)

    def seat_label(self, seats_per_row=4):
        # Convert seat number (1-based) to label like A1, A2, B1, etc.
        row = (self.seat_number - 1) // seats_per_row
        col = (self.seat_number - 1) % seats_per_row + 1
        return f"{chr(65 + row)}{col}"

    def __str__(self):
        return f"Ticket {self.id} for {self.booking.passenger_name} (Seat {self.seat_number})"
