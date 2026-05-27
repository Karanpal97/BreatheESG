"""
IATA airport codes → (latitude, longitude).
Covers major international airports relevant to business travel.
Used to compute great-circle distance when Concur doesn't supply Distance_km.
"""

import math

AIRPORT_COORDS = {
    # UK
    'LHR': (51.4775, -0.4614),   # London Heathrow
    'LGW': (51.1537, -0.1821),   # London Gatwick
    'MAN': (53.3537, -2.2750),   # Manchester
    'EDI': (55.9500, -3.3725),   # Edinburgh
    'BHX': (52.4539, -1.7480),   # Birmingham
    'GLA': (55.8642, -4.4331),   # Glasgow
    'BRS': (51.3827, -2.7191),   # Bristol

    # Europe
    'CDG': (49.0097,  2.5478),   # Paris Charles de Gaulle
    'AMS': (52.3086,  4.7639),   # Amsterdam Schiphol
    'FRA': (50.0379,  8.5622),   # Frankfurt
    'MUC': (48.3538, 11.7861),   # Munich
    'MAD': (40.4719, -3.5626),   # Madrid
    'BCN': (41.2971,  2.0785),   # Barcelona
    'FCO': (41.8003, 12.2389),   # Rome Fiumicino
    'ZRH': (47.4582,  8.5555),   # Zurich
    'VIE': (48.1103, 16.5697),   # Vienna
    'CPH': (55.6180, 12.6560),   # Copenhagen
    'DUB': (53.4213, -6.2701),   # Dublin
    'BRU': (50.9010,  4.4844),   # Brussels
    'OSL': (60.1976, 11.1004),   # Oslo
    'ARN': (59.6519, 17.9186),   # Stockholm Arlanda
    'HEL': (60.3172, 24.9633),   # Helsinki
    'WAW': (52.1657, 20.9671),   # Warsaw
    'PRG': (50.1008, 14.2600),   # Prague
    'BUD': (47.4298, 19.2611),   # Budapest

    # North America
    'JFK': (40.6413, -73.7781),  # New York JFK
    'EWR': (40.6895, -74.1745),  # New York Newark
    'LAX': (33.9425, -118.4081), # Los Angeles
    'ORD': (41.9742, -87.9073),  # Chicago O'Hare
    'ATL': (33.6407, -84.4277),  # Atlanta
    'DFW': (32.8998, -97.0403),  # Dallas/Fort Worth
    'SFO': (37.6213, -122.3790), # San Francisco
    'BOS': (42.3656, -71.0096),  # Boston
    'MIA': (25.7959, -80.2870),  # Miami
    'DEN': (39.8561, -104.6737), # Denver
    'SEA': (47.4502, -122.3088), # Seattle
    'YYZ': (43.6777, -79.6248),  # Toronto
    'YVR': (49.1967, -123.1815), # Vancouver

    # Asia Pacific
    'DXB': (25.2532, 55.3657),   # Dubai
    'SIN': (1.3644, 103.9915),   # Singapore Changi
    'HKG': (22.3080, 113.9185),  # Hong Kong
    'NRT': (35.7720, 140.3929),  # Tokyo Narita
    'HND': (35.5494, 139.7798),  # Tokyo Haneda
    'ICN': (37.4602, 126.4407),  # Seoul Incheon
    'PVG': (31.1443, 121.8083),  # Shanghai Pudong
    'PEK': (40.0799, 116.6031),  # Beijing Capital
    'BOM': (19.0896, 72.8656),   # Mumbai
    'DEL': (28.5562, 77.1000),   # Delhi
    'BLR': (13.1979, 77.7063),   # Bangalore
    'SYD': (-33.9399, 151.1753), # Sydney
    'MEL': (-37.6690, 144.8410), # Melbourne
    'AKL': (-37.0082, 174.7850), # Auckland

    # Middle East & Africa
    'DOH': (25.2731, 51.6081),   # Doha
    'AUH': (24.4330, 54.6511),   # Abu Dhabi
    'JNB': (-26.1367, 28.2411),  # Johannesburg
    'NBO': (-1.3192, 36.9275),   # Nairobi
    'CAI': (30.1219, 31.4056),   # Cairo

    # Latin America
    'GRU': (-23.4356, -46.4731), # São Paulo Guarulhos
    'EZE': (-34.8222, -58.5358), # Buenos Aires
    'BOG': (4.7016, -74.1469),   # Bogotá
    'LIM': (-12.0219, -77.1143), # Lima
    'SCL': (-33.3930, -70.7858), # Santiago
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def flight_distance_km(origin: str, destination: str, uplift: float = 1.08) -> tuple[float, bool]:
    """
    Returns (distance_km, success).
    Applies 8% uplift to account for non-direct routing (DEFRA methodology).
    Returns success=False if either airport code is unknown.
    """
    o = origin.upper().strip()
    d = destination.upper().strip()
    if o not in AIRPORT_COORDS or d not in AIRPORT_COORDS:
        return 0.0, False
    lat1, lon1 = AIRPORT_COORDS[o]
    lat2, lon2 = AIRPORT_COORDS[d]
    dist = haversine_km(lat1, lon1, lat2, lon2)
    return dist * uplift, True
