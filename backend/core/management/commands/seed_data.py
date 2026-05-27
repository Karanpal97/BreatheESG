from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Company, EmissionFactor, PlantLookup

User = get_user_model()

PLANTS = [
    {'plant_code': '1000', 'plant_name': 'Hamburg Plant', 'facility_name': 'Hamburg Logistics Hub', 'country_code': 'DE'},
    {'plant_code': '2000', 'plant_name': 'Munich Plant', 'facility_name': 'Munich Manufacturing', 'country_code': 'DE'},
    {'plant_code': '3000', 'plant_name': 'London Depot', 'facility_name': 'London Distribution', 'country_code': 'GB'},
    {'plant_code': '4000', 'plant_name': 'Paris Office', 'facility_name': 'Paris HQ', 'country_code': 'FR'},
]

EMISSION_FACTORS = [
    # Scope 1 fuels
    {'activity_type': 'diesel',          'factor_value': 2.68224, 'unit': 'kg_co2e_per_litre',  'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': 'Road diesel combustion'},
    {'activity_type': 'petrol',          'factor_value': 2.31365, 'unit': 'kg_co2e_per_litre',  'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': 'Petrol/gasoline combustion'},
    {'activity_type': 'lpg',             'factor_value': 1.56388, 'unit': 'kg_co2e_per_litre',  'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': 'LPG combustion'},
    {'activity_type': 'natural_gas_m3',  'factor_value': 2.04269, 'unit': 'kg_co2e_per_m3',     'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': 'Natural gas, volume-based'},
    {'activity_type': 'natural_gas_kwh', 'factor_value': 0.20272, 'unit': 'kg_co2e_per_kwh',    'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': 'Natural gas, energy-based'},
    # Scope 2 electricity
    {'activity_type': 'grid_uk',         'factor_value': 0.23314, 'unit': 'kg_co2e_per_kwh',    'source_dataset': 'DEFRA 2024', 'country_code': 'GB', 'notes': 'UK National Grid 2024'},
    {'activity_type': 'grid_us',         'factor_value': 0.38600, 'unit': 'kg_co2e_per_kwh',    'source_dataset': 'EPA 2023',   'country_code': 'US', 'notes': 'US average grid'},
    {'activity_type': 'grid_eu',         'factor_value': 0.27500, 'unit': 'kg_co2e_per_kwh',    'source_dataset': 'EEA 2023',   'country_code': '',   'notes': 'EU average grid'},
    # Scope 3 flights
    {'activity_type': 'flight_economy_short',  'factor_value': 0.25498, 'unit': 'kg_co2e_per_pkm', 'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': '<3700km, with RFI'},
    {'activity_type': 'flight_economy_long',   'factor_value': 0.19510, 'unit': 'kg_co2e_per_pkm', 'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': '>=3700km, with RFI'},
    {'activity_type': 'flight_business_short', 'factor_value': 0.38248, 'unit': 'kg_co2e_per_pkm', 'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': '<3700km business class'},
    {'activity_type': 'flight_business_long',  'factor_value': 0.42879, 'unit': 'kg_co2e_per_pkm', 'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': '>=3700km business class'},
    {'activity_type': 'flight_first_long',     'factor_value': 0.78039, 'unit': 'kg_co2e_per_pkm', 'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': '>=3700km first class'},
    # Scope 3 hotel
    {'activity_type': 'hotel_night',     'factor_value': 22.00,   'unit': 'kg_co2e_per_night', 'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': 'Average hotel room-night'},
    # Scope 3 ground transport
    {'activity_type': 'taxi',            'factor_value': 0.14919, 'unit': 'kg_co2e_per_km',    'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': 'Taxi/rideshare average'},
    {'activity_type': 'train',           'factor_value': 0.03549, 'unit': 'kg_co2e_per_km',    'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': 'National rail average UK'},
    {'activity_type': 'car_rental',      'factor_value': 0.19190, 'unit': 'kg_co2e_per_km',    'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': 'Average rental car (petrol)'},
    {'activity_type': 'bus',             'factor_value': 0.10484, 'unit': 'kg_co2e_per_km',    'source_dataset': 'DEFRA 2024', 'country_code': '', 'notes': 'Local bus average'},
]


class Command(BaseCommand):
    help = 'Seeds demo data: company, users, emission factors, plant lookup'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Company
        company, _ = Company.objects.get_or_create(
            slug='acme-corp',
            defaults={'name': 'Acme Corporation'}
        )
        self.stdout.write(f'  Company: {company.name}')

        # Users
        admin_user, created = User.objects.get_or_create(
            username='admin@acme.com',
            defaults={
                'email': 'admin@acme.com',
                'first_name': 'Sarah',
                'last_name': 'Chen',
                'company': company,
                'role': User.ROLE_ADMIN,
                'is_staff': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
        self.stdout.write(f'  Admin user: admin@acme.com / admin123')

        analyst, created = User.objects.get_or_create(
            username='analyst@acme.com',
            defaults={
                'email': 'analyst@acme.com',
                'first_name': 'James',
                'last_name': 'Patel',
                'company': company,
                'role': User.ROLE_ANALYST,
            }
        )
        if created:
            analyst.set_password('analyst123')
            analyst.save()
        self.stdout.write(f'  Analyst user: analyst@acme.com / analyst123')

        # Emission factors
        for ef_data in EMISSION_FACTORS:
            EmissionFactor.objects.get_or_create(
                activity_type=ef_data['activity_type'],
                defaults=ef_data
            )
        self.stdout.write(f'  Loaded {len(EMISSION_FACTORS)} emission factors')

        # Plant lookup
        for plant in PLANTS:
            PlantLookup.objects.get_or_create(
                plant_code=plant['plant_code'],
                company=company,
                defaults=plant
            )
        self.stdout.write(f'  Loaded {len(PLANTS)} plant codes')

        self.stdout.write(self.style.SUCCESS('\nSeed complete! Login: admin@acme.com / admin123'))
