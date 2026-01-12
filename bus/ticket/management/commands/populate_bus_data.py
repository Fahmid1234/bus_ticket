from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from ticket.models import Bus, Route, Schedule
import random

class Command(BaseCommand):
    help = 'Populate database with bus routes, buses, and schedules from Bangladesh'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate bus data...')
        
        # Clear existing data
        Schedule.objects.all().delete()
        Bus.objects.all().delete()
        Route.objects.all().delete()
        
        # Popular bus companies in Bangladesh
        bus_companies = [
            'Green Line Paribahan',
            'Shyamoli Paribahan',
            'Hanif Enterprise',
            'Ena Transport',
            'Unique Service',
            'Soudia Coach',
            'Desh Travels',
            'Eagle Paribahan',
            'BRTC',
            'Dhaka Express',
            'Saintmartin Paribahan',
            'Sakura Paribahan',
            'Tungipara Express',
            'Royal Coach',
            'Nabil Paribahan',
            'Alhamra Paribahan',
            'Falguni Paribahan',
            'Bablu Enterprise',
            'Mamun Express',
            'Sohag Paribahan',
            'Shanti Paribahan',
            'Bikash Paribahan',
            'Jahan Paribahan',
            'Kuakata Express',
            'Sundarban Express'
        ]
        
        # Popular routes in Bangladesh with realistic distances
        routes_data = [
            # Major routes from Dhaka
            ('Dhaka', 'Chittagong', 264),
            ('Dhaka', 'Sylhet', 238),
            ('Dhaka', 'Rajshahi', 267),
            ('Dhaka', 'Khulna', 335),
            ('Dhaka', 'Barisal', 169),
            ('Dhaka', 'Rangpur', 315),
            ('Dhaka', 'Mymensingh', 120),
            ('Dhaka', 'Comilla', 97),
            ('Dhaka', 'Jessore', 267),
            ('Dhaka', 'Bogra', 197),
            ('Dhaka', 'Dinajpur', 340),
            ('Dhaka', 'Pabna', 180),
            ('Dhaka', 'Kushtia', 220),
            ('Dhaka', 'Faridpur', 85),
            ('Dhaka', 'Tangail', 77),
            ('Dhaka', 'Gazipur', 35),
            ('Dhaka', 'Narayanganj', 20),
            ('Dhaka', 'Narsingdi', 50),
            ('Dhaka', 'Kishoreganj', 145),
            ('Dhaka', 'Netrokona', 165),
            ('Dhaka', 'Sunamganj', 280),
            ('Dhaka', 'Habiganj', 200),
            ('Dhaka', 'Brahmanbaria', 110),
            ('Dhaka', 'Chandpur', 120),
            ('Dhaka', 'Feni', 160),
            ('Dhaka', 'Noakhali', 150),
            ('Dhaka', 'Lakshmipur', 140),
            ('Dhaka', 'Cox\'s Bazar', 414),
            ('Dhaka', 'Bandarban', 350),
            ('Dhaka', 'Rangamati', 320),
            ('Dhaka', 'Khagrachari', 310),
            
            # Inter-city routes
            ('Chittagong', 'Sylhet', 242),
            ('Chittagong', 'Cox\'s Bazar', 150),
            ('Chittagong', 'Bandarban', 100),
            ('Chittagong', 'Rangamati', 80),
            ('Chittagong', 'Khagrachari', 90),
            ('Chittagong', 'Feni', 60),
            ('Chittagong', 'Noakhali', 70),
            ('Chittagong', 'Lakshmipur', 80),
            ('Chittagong', 'Chandpur', 120),
            ('Chittagong', 'Comilla', 167),
            ('Chittagong', 'Brahmanbaria', 180),
            ('Chittagong', 'Dhaka', 264),
            
            ('Sylhet', 'Chittagong', 242),
            ('Sylhet', 'Sunamganj', 60),
            ('Sylhet', 'Habiganj', 80),
            ('Sylhet', 'Moulvibazar', 40),
            ('Sylhet', 'Kishoreganj', 120),
            ('Sylhet', 'Netrokona', 140),
            ('Sylhet', 'Dhaka', 238),
            
            ('Rajshahi', 'Khulna', 280),
            ('Rajshahi', 'Bogra', 70),
            ('Rajshahi', 'Pabna', 60),
            ('Rajshahi', 'Natore', 30),
            ('Rajshahi', 'Naogaon', 50),
            ('Rajshahi', 'Chapainawabganj', 80),
            ('Rajshahi', 'Dhaka', 267),
            
            ('Khulna', 'Jessore', 60),
            ('Khulna', 'Kushtia', 80),
            ('Khulna', 'Bagerhat', 40),
            ('Khulna', 'Satkhira', 70),
            ('Khulna', 'Barisal', 120),
            ('Khulna', 'Dhaka', 335),
            
            ('Barisal', 'Chittagong', 200),
            ('Barisal', 'Khulna', 120),
            ('Barisal', 'Pirojpur', 30),
            ('Barisal', 'Bhola', 80),
            ('Barisal', 'Patuakhali', 60),
            ('Barisal', 'Barguna', 70),
            ('Barisal', 'Jhalokati', 40),
            ('Barisal', 'Dhaka', 169),
            
            ('Rangpur', 'Dinajpur', 60),
            ('Rangpur', 'Kurigram', 80),
            ('Rangpur', 'Lalmonirhat', 50),
            ('Rangpur', 'Nilphamari', 40),
            ('Rangpur', 'Panchagarh', 70),
            ('Rangpur', 'Thakurgaon', 90),
            ('Rangpur', 'Bogra', 120),
            ('Rangpur', 'Dhaka', 315),
            
            ('Bogra', 'Rangpur', 120),
            ('Bogra', 'Rajshahi', 70),
            ('Bogra', 'Pabna', 80),
            ('Bogra', 'Sirajganj', 60),
            ('Bogra', 'Jamalpur', 100),
            ('Bogra', 'Dhaka', 197),
            
            ('Jessore', 'Khulna', 60),
            ('Jessore', 'Kushtia', 40),
            ('Jessore', 'Magura', 30),
            ('Jessore', 'Jhenaidah', 25),
            ('Jessore', 'Narail', 35),
            ('Jessore', 'Dhaka', 267),
            
            ('Comilla', 'Chittagong', 167),
            ('Comilla', 'Brahmanbaria', 40),
            ('Comilla', 'Chandpur', 30),
            ('Comilla', 'Feni', 70),
            ('Comilla', 'Noakhali', 80),
            ('Comilla', 'Dhaka', 97),
        ]
        
        # Bus types with realistic capacities based on Bangladesh bus models
        bus_types = [
            ('Economy Class', 45),      # Standard economy buses
            ('Business Class', 35),     # Premium business class
            ('Hino RN8', 42),           # Hino RN8 model
            ('Hino RM2', 38),           # Hino RM2 model  
            ('Hyundai Universe', 40),   # Hyundai Universe luxury
            ('Hyundai County', 35),     # Hyundai County premium
            ('Hino RK8', 44),           # Hino RK8 standard
            ('Hino RN8J', 40),          # Hino RN8J premium
            ('Hyundai Aero', 38),       # Hyundai Aero luxury
            ('Hino RM2J', 36),          # Hino RM2J business
        ]
        
        # Create routes
        routes = []
        for origin, destination, distance in routes_data:
            route, created = Route.objects.get_or_create(
                origin=origin,
                destination=destination,
                defaults={'distance_km': distance}
            )
            routes.append(route)
            if created:
                self.stdout.write(f'Created route: {route}')
        
        # Create buses
        buses = []
        for i in range(100):  # Create 100 buses
            company = random.choice(bus_companies)
            bus_type, default_capacity = random.choice(bus_types)
            capacity = default_capacity + random.randint(-5, 5)  # Vary capacity slightly
            
            # Generate realistic number plates
            if bus_type == 'Economy Class':
                plate = f"Dhaka Metro-{random.randint(1000, 9999)}"
            elif bus_type == 'Business Class':
                plate = f"Dhaka Metro-{random.randint(1000, 9999)}"
            else:
                plate = f"Dhaka Metro-{random.randint(1000, 9999)}"
            
            bus, created = Bus.objects.get_or_create(
                number_plate=plate,
                defaults={
                    'name': f"{company} {bus_type}",
                    'capacity': max(20, capacity),  # Ensure minimum capacity
                    'bus_type': bus_type
                }
            )
            buses.append(bus)
            if created:
                self.stdout.write(f'Created bus: {bus}')
        
        # Create schedules with realistic timing patterns
        # All departure times are now at round intervals (every 30 minutes)
        # This ensures consistent, predictable departure times like 11:00, 11:30, 12:00, etc.
        # Start from tomorrow to ensure schedules are in the future
        base_time = (timezone.now() + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
        
        # Define departure time patterns based on route distance with round times
        def get_departure_times(distance):
            # Helper function to generate round times
            def generate_round_times(start_hour, end_hour, interval_minutes):
                times = []
                for hour in range(start_hour, end_hour + 1):
                    for minute in range(0, 60, interval_minutes):
                        times.append((hour, minute))
                return times
            
            if distance <= 100:  # Short routes (local) - every 15 minutes for more frequent service
                return generate_round_times(6, 21, 15)
            elif distance <= 200:  # Medium routes - every 30 minutes
                return generate_round_times(6, 20, 30)
            elif distance <= 300:  # Long routes - every 30 minutes
                return generate_round_times(6, 18, 30)
            else:  # Very long routes - every 30 minutes
                return generate_round_times(6, 16, 30)
        
        # Real Bangladesh bus fare calculation based on actual prices
        def calculate_real_fare(distance, bus_type):
            # Base fare rates per km (as of 2024-2025)
            base_rates = {
                'Economy Class': 1.8,      # 1.8 BDT per km
                'Business Class': 7.0,     # 7.0 BDT per km
                'Hino RN8': 4.0,           # 4.0 BDT per km
                'Hino RM2': 3.0,           # 3.0 BDT per km
                'Hyundai Universe': 5.0,   # 5.0 BDT per km
                'Hyundai County': 4.0,     # 4.0 BDT per km
                'Hino RK8': 5.0,           # 5.0 BDT per km
                'Hino RN8J': 4.0,          # 4.0 BDT per km
                'Hyundai Aero': 4.0,       # 4.0 BDT per km
                'Hino RM2J': 3.0,          # 3.0 BDT per km
            }
            
            base_rate = base_rates.get(bus_type, 2.5)
            base_fare = distance * base_rate
            
            # Add distance-based adjustments (longer routes get slight discount)
            if distance > 300:
                base_fare *= 0.95  # 5% discount for very long routes
            elif distance > 200:
                base_fare *= 0.98  # 2% discount for long routes
            
            # Add minimum fare protection
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
            
            # Ensure minimum fare is maintained after rounding
            final_fare = max(final_fare, min_fare)
            
            return final_fare
        
        for route in routes:
            departure_times = get_departure_times(route.distance_km)
            
            # Create schedules for next 7 days (starting from tomorrow)
            for day_offset in range(7):
                for hour, minute in departure_times:
                    # Use exact round times (no randomness)
                    departure_time = base_time + timedelta(
                        days=day_offset,
                        hours=hour,
                        minutes=minute
                    )
                    
                    # Calculate realistic travel time based on distance and road conditions
                    if route.distance_km <= 100:
                        avg_speed = 45  # Local roads, slower
                    elif route.distance_km <= 200:
                        avg_speed = 55  # Mixed roads
                    elif route.distance_km <= 300:
                        avg_speed = 65  # Highways
                    else:
                        avg_speed = 70  # Express highways
                    
                    travel_hours = route.distance_km / avg_speed
                    arrival_time = departure_time + timedelta(hours=travel_hours)
                    
                    # Select random bus and calculate realistic fare
                    bus = random.choice(buses)
                    fare = calculate_real_fare(route.distance_km, bus.bus_type)
                    
                    schedule, created = Schedule.objects.get_or_create(
                        bus=bus,
                        route=route,
                        departure_time=departure_time,
                        defaults={
                            'arrival_time': arrival_time,
                            'fare': fare
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'Created schedule: {schedule}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated database with {Route.objects.count()} routes, '
                f'{Bus.objects.count()} buses, and {Schedule.objects.count()} schedules!'
            )
        ) 