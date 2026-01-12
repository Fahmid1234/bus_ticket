from django.apps import AppConfig


class TicketConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ticket'
    verbose_name = 'Bus Ticket System'

    def ready(self):
        # This will ensure template tags are loaded
        import ticket.templatetags.ticket_tags
