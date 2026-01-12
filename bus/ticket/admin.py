from django.contrib import admin
from .models import Bus, Route, Schedule, Booking, Ticket

class BusAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'number_plate', 'capacity', 'bus_type')
    search_fields = ('name', 'number_plate', 'bus_type')
    list_filter = ('bus_type',)

class RouteAdmin(admin.ModelAdmin):
    list_display = ('id', 'origin', 'destination', 'distance_km')
    search_fields = ('origin', 'destination')

class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'bus', 'route', 'departure_time', 'arrival_time', 'fare')
    search_fields = ('bus__name', 'route__origin', 'route__destination')
    list_filter = ('bus', 'route', 'departure_time')

class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'schedule', 'user', 'passenger_name', 'passenger_email', 'seats_booked', 'booking_time', 'is_confirmed')
    search_fields = ('passenger_name', 'passenger_email', 'user__username')
    list_filter = ('is_confirmed', 'schedule')

class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'seat_number', 'seat_label_display', 'issued_at')
    search_fields = ('booking__passenger_name', 'booking__passenger_email')
    list_filter = ('booking',)
    
    def seat_label_display(self, obj):
        return obj.seat_label()
    seat_label_display.short_description = 'Seat Label'

admin.site.register(Bus, BusAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(Ticket, TicketAdmin)
