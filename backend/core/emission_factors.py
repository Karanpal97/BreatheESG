# DEFRA 2024 emission factors
# kg CO2e per unit of activity

EMISSION_FACTORS = {
    # Scope 1 — Fuels (kg CO2e per litre unless noted)
    'diesel':           {'factor': 2.68224, 'unit': 'L',   'scope': 'SCOPE_1'},
    'petrol':           {'factor': 2.31365, 'unit': 'L',   'scope': 'SCOPE_1'},
    'lpg':              {'factor': 1.56388, 'unit': 'L',   'scope': 'SCOPE_1'},
    'natural_gas_m3':   {'factor': 2.04269, 'unit': 'm3',  'scope': 'SCOPE_1'},
    'natural_gas_kwh':  {'factor': 0.20272, 'unit': 'kWh', 'scope': 'SCOPE_1'},

    # Scope 2 — Grid electricity (kg CO2e per kWh)
    'grid_uk':          {'factor': 0.23314, 'unit': 'kWh', 'scope': 'SCOPE_2'},
    'grid_us':          {'factor': 0.38600, 'unit': 'kWh', 'scope': 'SCOPE_2'},
    'grid_eu':          {'factor': 0.27500, 'unit': 'kWh', 'scope': 'SCOPE_2'},

    # Scope 3 — Flights (kg CO2e per passenger-km, with radiative forcing)
    'flight_economy_short':   {'factor': 0.25498, 'unit': 'pkm', 'scope': 'SCOPE_3'},
    'flight_economy_long':    {'factor': 0.19510, 'unit': 'pkm', 'scope': 'SCOPE_3'},
    'flight_business_short':  {'factor': 0.38248, 'unit': 'pkm', 'scope': 'SCOPE_3'},
    'flight_business_long':   {'factor': 0.42879, 'unit': 'pkm', 'scope': 'SCOPE_3'},
    'flight_first_long':      {'factor': 0.78039, 'unit': 'pkm', 'scope': 'SCOPE_3'},

    # Scope 3 — Hotels (kg CO2e per room-night)
    'hotel_night':      {'factor': 22.00, 'unit': 'nights', 'scope': 'SCOPE_3'},

    # Scope 3 — Ground transport (kg CO2e per km)
    'taxi':             {'factor': 0.14919, 'unit': 'km', 'scope': 'SCOPE_3'},
    'train':            {'factor': 0.03549, 'unit': 'km', 'scope': 'SCOPE_3'},
    'car_rental':       {'factor': 0.19190, 'unit': 'km', 'scope': 'SCOPE_3'},
    'bus':              {'factor': 0.10484, 'unit': 'km', 'scope': 'SCOPE_3'},
}

# SAP material number → fuel type mapping
MATERIAL_FUEL_MAP = {
    '1000024': 'diesel',
    '1000025': 'petrol',
    '1000031': 'natural_gas_m3',
    '1000032': 'lpg',
    '1000040': 'diesel',   # Red diesel
    '1000041': 'diesel',   # HVO (simplified; in prod use separate EF)
    '2000010': 'diesel',
    '2000011': 'petrol',
}

# Posting text keyword → fuel type fallback (if material not in map)
POSTING_TEXT_FUEL_KEYWORDS = {
    'diesel': 'diesel',
    'kraftstoff': 'diesel',       # German for fuel
    'benzin': 'petrol',           # German for petrol
    'erdgas': 'natural_gas_m3',   # German for natural gas
    'flüssiggas': 'lpg',
    'lpg': 'lpg',
    'petrol': 'petrol',
    'gasoline': 'petrol',
    'gas': 'natural_gas_m3',
}


def get_flight_ef_key(cabin_class: str, distance_km: float) -> str:
    """Return the emission factor key for a flight based on cabin and distance."""
    cabin = cabin_class.lower().strip()
    is_long = distance_km >= 3700

    if 'business' in cabin:
        return 'flight_business_long' if is_long else 'flight_business_short'
    elif 'first' in cabin:
        return 'flight_first_long' if is_long else 'flight_business_long'
    else:
        return 'flight_economy_long' if is_long else 'flight_economy_short'
