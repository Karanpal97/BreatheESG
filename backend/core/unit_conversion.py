"""
Unit conversion table.
All conversions normalize to SI base units used in emission calculations.
"""

# To litres
TO_LITRES = {
    'l':    1.0,
    'ltr':  1.0,
    'litre': 1.0,
    'litres': 1.0,
    'liter': 1.0,
    'liters': 1.0,
    'gal':  3.78541,    # US gallon
    'gal_us': 3.78541,
    'gal_uk': 4.54609,  # Imperial gallon
    'ukgal': 4.54609,
    'qt':   0.946353,   # US quart
    'fl_oz': 0.0295735,
}

# To kilograms (for fuel by weight)
TO_KG = {
    'kg':   1.0,
    'kilo': 1.0,
    'g':    0.001,
    'lb':   0.453592,
    'lbs':  0.453592,
    'ton':  1000.0,
    'tonne': 1000.0,
    't':    1000.0,
    'mt':   1000.0,
}

# To cubic metres (gas)
TO_M3 = {
    'm3':   1.0,
    'cbm':  1.0,
    'ft3':  0.0283168,
    'cf':   0.0283168,
    'mcf':  28.3168,    # thousand cubic feet
}

# To kWh (electricity)
TO_KWH = {
    'kwh':  1.0,
    'kw·h': 1.0,
    'mwh':  1000.0,
    'gwh':  1000000.0,
}

# To kilometres
TO_KM = {
    'km':   1.0,
    'mi':   1.60934,
    'miles': 1.60934,
    'nmi':  1.852,     # nautical mile (used in aviation)
}


def normalize_to_litres(value: float, unit: str) -> tuple[float, bool]:
    """Returns (converted_value, success). success=False if unit unknown."""
    key = unit.lower().strip()
    if key in TO_LITRES:
        return value * TO_LITRES[key], True
    return value, False


def normalize_to_m3(value: float, unit: str) -> tuple[float, bool]:
    key = unit.lower().strip()
    if key in TO_M3:
        return value * TO_M3[key], True
    return value, False


def normalize_to_kg(value: float, unit: str) -> tuple[float, bool]:
    key = unit.lower().strip()
    if key in TO_KG:
        return value * TO_KG[key], True
    return value, False


def normalize_to_kwh(value: float, unit: str) -> tuple[float, bool]:
    key = unit.lower().strip()
    if key in TO_KWH:
        return value * TO_KWH[key], True
    return value, False


def normalize_to_km(value: float, unit: str) -> tuple[float, bool]:
    key = unit.lower().strip()
    if key in TO_KM:
        return value * TO_KM[key], True
    return value, False


# SAP UoM codes → normalization function + target unit
SAP_UOM_HANDLERS = {
    # Litres
    'l':   ('litres', normalize_to_litres),
    'ltr': ('litres', normalize_to_litres),
    'gal': ('litres', normalize_to_litres),
    'gl':  ('litres', normalize_to_litres),
    # Kilograms
    'kg':  ('kg', normalize_to_kg),
    'lb':  ('kg', normalize_to_kg),
    'g':   ('kg', normalize_to_kg),
    't':   ('kg', normalize_to_kg),
    'to':  ('kg', normalize_to_kg),  # SAP code for Tonne
    # Cubic metres
    'm3':  ('m3', normalize_to_m3),
    'ft3': ('m3', normalize_to_m3),
    # Energy
    'kwh': ('kwh', normalize_to_kwh),
    'mwh': ('kwh', normalize_to_kwh),
}
