"""
Utility electricity CSV parser.

Based on UK utility portal exports (E.ON, British Gas for Business, etc.).
Key real-world issues handled:
- Billing periods that DON'T align to calendar months (e.g. 23 Dec – 28 Jan)
- kVA rows mixed with kWh (demand vs. consumption)
- Estimated vs. actual meter reads
- MPAN validation (13-digit UK Meter Point Administration Number)
- Reading delta verification (Current - Previous ≈ Units_Consumed)
"""

import io
import re
import pandas as pd
from datetime import datetime
from decimal import Decimal

from core.emission_factors import EMISSION_FACTORS

PARSER_VERSION = 'utility_electricity_v1'

# UK grid emission factor (DEFRA 2024)
GRID_EF = EMISSION_FACTORS['grid_uk']['factor']  # kg CO2e per kWh

COLUMN_MAP = {
    'account_number':      'account_number',
    'account number':      'account_number',
    'account_no':          'account_number',
    'accountnumber':       'account_number',

    'mpan':                'mpan',
    'meter_point_admin_number': 'mpan',
    'meter point':         'mpan',

    'site_address':        'site_address',
    'site address':        'site_address',
    'address':             'site_address',
    'location':            'site_address',
    'facility':            'site_address',

    'meter_serial_number': 'meter_serial',
    'meter serial':        'meter_serial',
    'meter_id':            'meter_serial',
    'meter id':            'meter_serial',

    'read_date_from':      'period_start',
    'date from':           'period_start',
    'start_date':          'period_start',
    'billing_start':       'period_start',
    'from':                'period_start',

    'read_date_to':        'period_end',
    'date to':             'period_end',
    'end_date':            'period_end',
    'billing_end':         'period_end',
    'to':                  'period_end',

    'previous_reading':    'read_previous',
    'prev_reading':        'read_previous',
    'opening_read':        'read_previous',

    'current_reading':     'read_current',
    'curr_reading':        'read_current',
    'closing_read':        'read_current',

    'units_consumed':      'units_consumed',
    'consumption':         'units_consumed',
    'usage':               'units_consumed',
    'usage_kwh':           'units_consumed',
    'kwh':                 'units_consumed',

    'unit':                'unit',
    'units':               'unit',
    'uom':                 'unit',

    'tariff_code':         'tariff_code',
    'tariff':              'tariff_code',
    'rate_schedule':       'tariff_code',

    'rate_p_per_kwh':      'rate_per_kwh',
    'rate':                'rate_per_kwh',

    'total_amount':        'total_amount',
    'total':               'total_amount',
    'amount':              'total_amount',
    'total_excl_vat':      'total_amount',

    'currency':            'currency',

    'read_method':         'read_method',
    'reading_type':        'read_method',
}


def _norm_col(c: str) -> str:
    return c.strip().lower().replace(' ', '_')


def _parse_date(val: str) -> datetime | None:
    if not val or str(val).strip() in ('', 'nan', 'NaT'):
        return None
    val = str(val).strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y', '%m/%d/%Y', '%d %b %Y', '%d %B %Y'):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def _validate_mpan(mpan: str) -> bool:
    """UK MPAN: 13 digits. Strip spaces/dashes."""
    clean = re.sub(r'[\s\-]', '', str(mpan))
    return bool(re.match(r'^\d{13}$', clean))


def parse(file_bytes: bytes, filename: str, grid_ef_key: str = 'grid_uk') -> list[dict]:
    ef_value = EMISSION_FACTORS.get(grid_ef_key, EMISSION_FACTORS['grid_uk'])['factor']

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

    # Normalize column names
    col_remap = {}
    for col in df.columns:
        norm = _norm_col(col)
        if norm in COLUMN_MAP:
            col_remap[col] = COLUMN_MAP[norm]
    df = df.rename(columns=col_remap)

    required = {'units_consumed'}
    missing = required - set(df.columns)
    if missing:
        return [{'row_number': 0, 'raw_data': {}, 'status': 'FAILED',
                 'errors': [f'Missing required columns: {missing}'], 'warnings': []}]

    results = []

    for idx, row in df.iterrows():
        row_num = idx + 2
        raw = row.to_dict()
        errors = []
        warnings = []

        # --- Consumption (kWh) ---
        raw_kwh = str(raw.get('units_consumed', '')).strip().replace(',', '')
        if not raw_kwh or raw_kwh in ('nan', ''):
            errors.append('Missing units_consumed')
            results.append({'row_number': row_num, 'raw_data': raw, 'status': 'FAILED',
                            'errors': errors, 'warnings': warnings})
            continue

        try:
            kwh = float(raw_kwh)
        except ValueError:
            errors.append(f'Non-numeric consumption: {raw_kwh}')
            results.append({'row_number': row_num, 'raw_data': raw, 'status': 'FAILED',
                            'errors': errors, 'warnings': warnings})
            continue

        if kwh < 0:
            errors.append(f'Negative consumption: {kwh}')
            results.append({'row_number': row_num, 'raw_data': raw, 'status': 'FAILED',
                            'errors': errors, 'warnings': warnings})
            continue

        # --- Unit check ---
        unit = str(raw.get('unit', 'kWh')).strip()
        if unit.lower() in ('kva', 'kva_demand', 'demand'):
            warnings.append(f'Unit is {unit} (demand charge, not consumption kWh) — cannot compute emissions directly')

        # --- MPAN validation ---
        mpan = str(raw.get('mpan', '')).strip()
        if mpan and mpan != 'nan':
            if not _validate_mpan(mpan):
                warnings.append(f'MPAN "{mpan}" does not match 13-digit UK format')
        else:
            warnings.append('No MPAN provided')

        # --- Reading delta check ---
        try:
            prev = float(str(raw.get('read_previous', 'nan')).replace(',', ''))
            curr = float(str(raw.get('read_current', 'nan')).replace(',', ''))
            delta = curr - prev
            if curr < prev:
                warnings.append(f'Current reading ({curr}) < previous ({prev}) — possible meter rollover or error')
            elif abs(delta - kwh) / max(kwh, 1) > 0.005:  # >0.5% tolerance
                warnings.append(
                    f'Reading delta ({delta:.2f}) differs from units_consumed ({kwh:.2f}) by >{0.5}%'
                )
        except (ValueError, TypeError):
            pass  # readings not present; not mandatory

        # --- Dates ---
        period_start = _parse_date(str(raw.get('period_start', '')))
        period_end = _parse_date(str(raw.get('period_end', '')))

        if period_start and period_end:
            days = (period_end - period_start).days
            if days > 92:  # longer than ~3 months
                warnings.append(f'Billing period is {days} days — unusually long')
            if days < 0:
                errors.append('period_end is before period_start')
                results.append({'row_number': row_num, 'raw_data': raw, 'status': 'FAILED',
                                'errors': errors, 'warnings': warnings})
                continue

        # --- Read method ---
        read_method = str(raw.get('read_method', '')).strip().lower()
        if 'estimated' in read_method or 'est' == read_method:
            warnings.append('Meter reading is estimated, not actual')

        # --- CO2e ---
        co2e = kwh * ef_value

        status = 'FAILED' if errors else ('SUSPICIOUS' if warnings else 'OK')

        results.append({
            'row_number': row_num,
            'raw_data': raw,
            'status': status,
            'errors': errors,
            'warnings': warnings,
            'scope': 'SCOPE_2',
            'activity_value': round(kwh, 4),
            'activity_unit': 'kWh',
            'activity_description': f'Grid electricity — {raw.get("site_address", raw.get("mpan", "Unknown site"))}',
            'emission_factor': ef_value,
            'emission_factor_source': 'DEFRA 2024 (UK Grid)',
            'co2e_kg': round(co2e, 4),
            'period_start': period_start.date() if period_start else None,
            'period_end': period_end.date() if period_end else None,
            'account_number': str(raw.get('account_number', '')).strip(),
            'mpan': mpan,
            'site_address': str(raw.get('site_address', '')).strip(),
            'meter_serial': str(raw.get('meter_serial', '')).strip(),
            'tariff_code': str(raw.get('tariff_code', '')).strip(),
            'unit': unit,
        })

    return results
