"""
Concur travel expense CSV parser.

Handles Concur Standard Accounting Extract / admin export flat files.
Three expense categories: Air, Hotel, Ground Transport.

Key real-world issues:
- Distance_km often blank for flights → compute via haversine on IATA codes
- Business/First class flagged automatically (high emission factor)
- Hotel: use check-in/check-out nights  
- Ground: emission factor varies by mode (taxi vs. train vs. car rental)
- Unknown IATA codes → FAILED
"""

import io
import pandas as pd
from datetime import datetime

from core.emission_factors import EMISSION_FACTORS, get_flight_ef_key
from core.airport_coords import flight_distance_km, AIRPORT_COORDS

PARSER_VERSION = 'travel_concur_v1'

COLUMN_MAP = {
    'report_id':            'report_id',
    'report_name':          'report_name',
    'employee_id':          'employee_id',
    'employee_name':        'employee_name',
    'department':           'department',
    'cost_center':          'cost_center',
    'expense_type':         'expense_type',
    'transaction_date':     'transaction_date',
    'date':                 'transaction_date',

    # Flight fields
    'origin_airport':       'origin_airport',
    'origin':               'origin_airport',
    'departure_airport':    'origin_airport',
    'from_airport':         'origin_airport',
    'destination_airport':  'destination_airport',
    'destination':          'destination_airport',
    'arrival_airport':      'destination_airport',
    'to_airport':           'destination_airport',
    'cabin_class':          'cabin_class',
    'class':                'cabin_class',
    'ticket_class':         'cabin_class',
    'distance_km':          'distance_km',
    'distance':             'distance_km',
    'flight_distance':      'distance_km',
    'airline':              'airline',
    'flight_number':        'flight_number',

    # Hotel fields
    'hotel_name':           'hotel_name',
    'property_name':        'hotel_name',
    'check_in_date':        'check_in_date',
    'check_in':             'check_in_date',
    'checkin_date':         'check_in_date',
    'check_out_date':       'check_out_date',
    'check_out':            'check_out_date',
    'checkout_date':        'check_out_date',
    'nights':               'nights',

    # Ground transport
    'ground_mode':          'ground_mode',
    'transport_mode':       'ground_mode',
    'mode':                 'ground_mode',
    'ground_distance_km':   'ground_distance_km',
    'pickup_location':      'pickup_location',
    'dropoff_location':     'dropoff_location',

    # Financial
    'amount':               'amount',
    'total_amount':         'amount',
    'currency':             'currency',
}

GROUND_MODE_EF = {
    'taxi':        'taxi',
    'cab':         'taxi',
    'uber':        'taxi',
    'lyft':        'taxi',
    'train':       'train',
    'rail':        'train',
    'metro':       'train',
    'underground': 'train',
    'tube':        'train',
    'car rental':  'car_rental',
    'car_rental':  'car_rental',
    'rental car':  'car_rental',
    'hire car':    'car_rental',
    'bus':         'bus',
    'coach':       'bus',
}


def _norm_col(c: str) -> str:
    return c.strip().lower().replace(' ', '_').replace('-', '_')


def _parse_date(val: str) -> datetime | None:
    if not val or str(val).strip() in ('', 'nan', 'NaT'):
        return None
    val = str(val).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%d.%m.%Y'):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def _parse_flight(row: dict, row_num: int) -> dict:
    errors, warnings = [], []

    origin = str(row.get('origin_airport', '')).strip().upper()
    dest = str(row.get('destination_airport', '')).strip().upper()
    cabin = str(row.get('cabin_class', 'economy')).strip()

    # Resolve distance
    dist_raw = str(row.get('distance_km', '')).strip()
    if dist_raw and dist_raw not in ('nan', '', '0'):
        try:
            distance_km = float(dist_raw)
            dist_source = 'provided'
        except ValueError:
            distance_km, dist_source = None, None
    else:
        distance_km, dist_source = None, None

    if distance_km is None:
        if not origin or not dest or origin == 'NAN' or dest == 'NAN':
            errors.append('Missing both distance_km and airport codes — cannot compute emissions')
            return {'row_number': row_num, 'raw_data': row, 'status': 'FAILED',
                    'errors': errors, 'warnings': warnings}

        dist_calc, ok = flight_distance_km(origin, dest)
        if not ok:
            errors.append(f'Unknown airport code(s): {origin} → {dest}')
            return {'row_number': row_num, 'raw_data': row, 'status': 'FAILED',
                    'errors': errors, 'warnings': warnings}

        distance_km = dist_calc
        dist_source = f'haversine({origin}→{dest}) ×1.08 uplift'
        warnings.append(f'Distance not provided; computed {distance_km:.0f} km via great-circle haversine')
    else:
        # Validate airport codes even if distance is given
        for code, label in [(origin, 'origin'), (dest, 'destination')]:
            if code and code != 'NAN' and code not in AIRPORT_COORDS:
                warnings.append(f'Airport code {code} ({label}) not in reference database — cannot verify')

    if distance_km > 15000:
        warnings.append(f'Distance {distance_km:.0f} km exceeds longest real direct flight — check data')

    ef_key = get_flight_ef_key(cabin, distance_km)
    ef_value = EMISSION_FACTORS[ef_key]['factor']
    co2e = distance_km * ef_value

    # Auto-flag premium cabins
    cabin_lower = cabin.lower()
    if 'business' in cabin_lower or 'first' in cabin_lower:
        warnings.append(f'{cabin} class: emission factor {ef_value} kg CO2e/pkm (significantly higher than economy)')

    date = _parse_date(str(row.get('transaction_date', '')))
    status = 'FAILED' if errors else ('SUSPICIOUS' if warnings else 'OK')

    return {
        'row_number': row_num,
        'raw_data': row,
        'status': status,
        'errors': errors,
        'warnings': warnings,
        'scope': 'SCOPE_3',
        'scope_3_category': 'Business Travel',
        'activity_value': round(distance_km, 2),
        'activity_unit': 'pkm',
        'activity_description': f'Flight {origin}→{dest} ({cabin}) — {dist_source}',
        'emission_factor': ef_value,
        'emission_factor_source': f'DEFRA 2024 ({ef_key})',
        'co2e_kg': round(co2e, 4),
        'period_start': date.date() if date else None,
        'period_end': date.date() if date else None,
        'department': str(row.get('department', '')).strip(),
        'cost_center': str(row.get('cost_center', '')).strip(),
        'source_document_ref': str(row.get('report_id', '')).strip(),
    }


def _parse_hotel(row: dict, row_num: int) -> dict:
    errors, warnings = [], []

    # Calculate nights
    nights_raw = str(row.get('nights', '')).strip()
    check_in = _parse_date(str(row.get('check_in_date', '')))
    check_out = _parse_date(str(row.get('check_out_date', '')))

    if nights_raw and nights_raw not in ('nan', ''):
        try:
            nights = float(nights_raw)
        except ValueError:
            nights = None
    else:
        nights = None

    if nights is None and check_in and check_out:
        nights = (check_out - check_in).days
        if nights <= 0:
            errors.append(f'Check-out ({check_out.date()}) is not after check-in ({check_in.date()})')

    if nights is None:
        errors.append('Cannot determine number of nights — missing nights, check_in_date, or check_out_date')
        return {'row_number': row_num, 'raw_data': row, 'status': 'FAILED',
                'errors': errors, 'warnings': warnings}

    ef_value = EMISSION_FACTORS['hotel_night']['factor']
    co2e = nights * ef_value

    hotel = str(row.get('hotel_name', 'Unknown Hotel')).strip()
    status = 'FAILED' if errors else ('SUSPICIOUS' if warnings else 'OK')

    return {
        'row_number': row_num,
        'raw_data': row,
        'status': status,
        'errors': errors,
        'warnings': warnings,
        'scope': 'SCOPE_3',
        'scope_3_category': 'Business Travel',
        'activity_value': round(nights, 0),
        'activity_unit': 'nights',
        'activity_description': f'Hotel: {hotel} ({int(nights)} nights)',
        'emission_factor': ef_value,
        'emission_factor_source': 'DEFRA 2024 (hotel)',
        'co2e_kg': round(co2e, 4),
        'period_start': check_in.date() if check_in else None,
        'period_end': check_out.date() if check_out else None,
        'department': str(row.get('department', '')).strip(),
        'cost_center': str(row.get('cost_center', '')).strip(),
        'source_document_ref': str(row.get('report_id', '')).strip(),
    }


def _parse_ground(row: dict, row_num: int) -> dict:
    errors, warnings = [], []

    mode_raw = str(row.get('ground_mode', '')).strip().lower()
    ef_key = GROUND_MODE_EF.get(mode_raw)
    if not ef_key:
        warnings.append(f'Unrecognised ground transport mode: "{mode_raw}" — defaulting to taxi')
        ef_key = 'taxi'

    dist_raw = str(row.get('ground_distance_km', '')).strip()
    if not dist_raw or dist_raw in ('nan', '', '0'):
        warnings.append('Ground distance not provided — cannot compute emissions accurately')
        # Fallback: use spend-based rough estimate can't be done without spend EF; flag as suspicious
        errors.append('Missing ground_distance_km — cannot calculate emissions')
        return {'row_number': row_num, 'raw_data': row, 'status': 'FAILED',
                'errors': errors, 'warnings': warnings}

    try:
        distance_km = float(dist_raw)
    except ValueError:
        errors.append(f'Non-numeric ground_distance_km: {dist_raw}')
        return {'row_number': row_num, 'raw_data': row, 'status': 'FAILED',
                'errors': errors, 'warnings': warnings}

    ef_value = EMISSION_FACTORS[ef_key]['factor']
    co2e = distance_km * ef_value

    date = _parse_date(str(row.get('transaction_date', '')))
    status = 'FAILED' if errors else ('SUSPICIOUS' if warnings else 'OK')

    return {
        'row_number': row_num,
        'raw_data': row,
        'status': status,
        'errors': errors,
        'warnings': warnings,
        'scope': 'SCOPE_3',
        'scope_3_category': 'Business Travel',
        'activity_value': round(distance_km, 2),
        'activity_unit': 'km',
        'activity_description': f'Ground transport ({mode_raw or ef_key}): {distance_km:.1f} km',
        'emission_factor': ef_value,
        'emission_factor_source': f'DEFRA 2024 ({ef_key})',
        'co2e_kg': round(co2e, 4),
        'period_start': date.date() if date else None,
        'period_end': date.date() if date else None,
        'department': str(row.get('department', '')).strip(),
        'cost_center': str(row.get('cost_center', '')).strip(),
        'source_document_ref': str(row.get('report_id', '')).strip(),
    }


EXPENSE_TYPE_HANDLERS = {
    'air': _parse_flight,
    'flight': _parse_flight,
    'airfare': _parse_flight,
    'hotel': _parse_hotel,
    'lodging': _parse_hotel,
    'accommodation': _parse_hotel,
    'ground': _parse_ground,
    'taxi': _parse_ground,
    'car rental': _parse_ground,
    'car_rental': _parse_ground,
    'rail': _parse_ground,
    'train': _parse_ground,
    'transport': _parse_ground,
}


def parse(file_bytes: bytes, filename: str) -> list[dict]:
    try:
        if filename.lower().endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        else:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding='utf-8-sig')
            except Exception:
                df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding='latin-1')
    except Exception as e:
        return [{'row_number': 0, 'raw_data': {}, 'status': 'FAILED',
                 'errors': [f'Cannot read file: {str(e)}'], 'warnings': []}]

    # Normalize cols
    col_remap = {}
    for col in df.columns:
        norm = _norm_col(col)
        if norm in COLUMN_MAP:
            col_remap[col] = COLUMN_MAP[norm]
    df = df.rename(columns=col_remap)

    if 'expense_type' not in df.columns:
        return [{'row_number': 0, 'raw_data': {}, 'status': 'FAILED',
                 'errors': ['Missing "expense_type" column — required to route rows to correct handler'],
                 'warnings': []}]

    results = []
    for idx, row in df.iterrows():
        row_num = idx + 2
        raw = row.to_dict()
        expense_type = str(raw.get('expense_type', '')).strip().lower()
        handler = EXPENSE_TYPE_HANDLERS.get(expense_type)

        if handler is None:
            results.append({
                'row_number': row_num, 'raw_data': raw,
                'status': 'FAILED',
                'errors': [f'Unknown expense_type: "{expense_type}"'], 'warnings': [],
            })
            continue

        results.append(handler(raw, row_num))

    return results
