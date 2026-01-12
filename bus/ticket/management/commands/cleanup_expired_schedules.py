from django.core.management.base import BaseCommand
from django.utils import timezone
from ticket.models import Schedule, Booking, Ticket
from django.db import transaction

class Command(BaseCommand):
    help = 'Clean up expired schedules and related data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        current_time = timezone.now()
        dry_run = options['dry_run']
        
        # Find expired schedules
        expired_schedules = Schedule.objects.filter(departure_time__lt=current_time)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {expired_schedules.count()} expired schedules'
                )
            )
            
            # Show some examples of what would be deleted
            for schedule in expired_schedules[:5]:
                self.stdout.write(
                    f'  - {schedule.route.origin} to {schedule.route.destination} '
                    f'({schedule.departure_time.strftime("%Y-%m-%d %H:%M")})'
                )
            
            if expired_schedules.count() > 5:
                self.stdout.write(f'  ... and {expired_schedules.count() - 5} more')
            
            return
        
        # Get count before deletion for reporting
        expired_count = expired_schedules.count()
        
        if expired_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No expired schedules found to clean up.')
            )
            return
        
        # Delete expired schedules and related data
        with transaction.atomic():
            # First, get all bookings for expired schedules
            expired_bookings = Booking.objects.filter(schedule__in=expired_schedules)
            booking_count = expired_bookings.count()
            
            # Delete tickets first (due to foreign key constraints)
            expired_tickets = Ticket.objects.filter(booking__in=expired_bookings)
            ticket_count = expired_tickets.count()
            
            # Delete in order: tickets -> bookings -> schedules
            expired_tickets.delete()
            expired_bookings.delete()
            expired_schedules.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully cleaned up {expired_count} expired schedules, '
                f'{booking_count} bookings, and {ticket_count} tickets.'
            )
        ) 