from django.core.management.base import BaseCommand
from django.db import transaction
from ticket.models import Schedule, Booking, Ticket

class Command(BaseCommand):
    help = 'Delete all schedules and related data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        # Get counts before deletion
        schedule_count = Schedule.objects.count()
        booking_count = Booking.objects.count()
        ticket_count = Ticket.objects.count()
        
        if schedule_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No schedules found in the database.')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {schedule_count} schedules, '
                    f'{booking_count} bookings, and {ticket_count} tickets'
                )
            )
            
            # Show some examples of what would be deleted
            self.stdout.write('\nSample schedules that would be deleted:')
            for schedule in Schedule.objects.select_related('bus', 'route')[:5]:
                self.stdout.write(
                    f'  - {schedule.route.origin} to {schedule.route.destination} '
                    f'({schedule.departure_time.strftime("%Y-%m-%d %H:%M")})'
                )
            
            if schedule_count > 5:
                self.stdout.write(f'  ... and {schedule_count - 5} more')
            
            return
        
        # Show what will be deleted
        self.stdout.write(
            self.style.WARNING(
                f'This will delete ALL schedules from the database:\n'
                f'- {schedule_count} schedules\n'
                f'- {booking_count} bookings\n'
                f'- {ticket_count} tickets\n'
                f'\nThis action cannot be undone!'
            )
        )
        
        if not force:
            confirm = input('\nAre you sure you want to continue? Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(
                    self.style.ERROR('Operation cancelled.')
                )
                return
        
        # Delete all data with proper cleanup
        with transaction.atomic():
            # Delete in order: tickets -> bookings -> schedules
            # This handles foreign key constraints properly
            deleted_tickets = Ticket.objects.all().delete()
            deleted_bookings = Booking.objects.all().delete()
            deleted_schedules = Schedule.objects.all().delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted all data:\n'
                f'- {deleted_schedules[0]} schedules\n'
                f'- {deleted_bookings[0]} bookings\n'
                f'- {deleted_tickets[0]} tickets'
            )
        ) 