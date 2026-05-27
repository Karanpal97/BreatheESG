"""
SAP flat-file parser (SE16N / FAGLL03 export style).

SAP exports from the GUI "Export to Spreadsheet" produce tab-delimited .txt
or .xlsx files with German column headers, dates in DD.MM.YYYY format, and
plant/material codes that need lookup tables. This parser handles all of that.
"""

import re
import io
import pandas as pd
from datetime import datetime
from decimal import Decimal

from core.emission_factors import EMISSION_FACTORS, MATERIAL_FUEL_MAP, POSTING_TEXT_FUEL_KEYWORDS
from core.unit_conversion import SAP_UOM_HANDLERS, normalize_to_litres, normalize_to_m3, normalize_to_kg

PARSER_VERSION = 'sap_fuel_v1'

# German → internal field name mapping (covers common SE16N and FAGLL03 exports)
COLUMN_MAP = {
    # Dates
    'buchungsdatum':      'posting_date',
    'belegdatum':         'document_date',
    'posting date':       'posting_date',
    'document date':      'document_date',

    # Document refs
    'belegnummer':        'document_number',
    'document number':    'document_number',
    'belegnum':           'document_number',

    # Org units
    'buchungskreis':      'company_code',
    'company code':       'company_code',
    'werk':               'plant_code',
    'plant':              'plant_code',
    'kostenstelle':       'cost_center',
    'cost center':        'cost_center',

    # Material
    'materialnummer':     'material_number',
    'material':           'material_number',
    'matnr':              'material_number',

    # Quantity & unit
    'menge':              'quantity',
    'quantity':           'quantity',
    'mengeneinheit':      'unit_of_measure',
    'basismengeneinheit': 'unit_of_measure',
    'meins':              'unit_of_measure',
    'unit':               'unit_of_measure',
    'uom':                'unit_of_measure',

    # Value
    'nettobetrag':        'net_amount',
    'net amount':         'net_amount',
    'netwr':              'net_amount',
    'betrag':             'net_amount',

    # Currency
    'waehrung':           'currency',
    'currency':           'currency',

    # Text
    'buchungstext':       'posting_text',
    'text':               'posting_text',
    'posting text':       'posting_text',
}


def _normalize_col(col: str) -> str:
    return col.strip().lower().replace('ä', 'a').replace('ö', 'o').replace('ü', 'u').replace('ß', 'ss')


def _parse_date(val: str) -> datetime | None:
    """Try multiple SAP date formats."""
    if not val or str(val).strip() in ('', 'nan', 'NaT'):
        return None
    val = str(val).strip()
    for fmt in ('%d.%m.%Y', '%Y%m%d', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def _detect_fuel_type(material: str, posting_text: str) -> str | None:
    """Resolve fuel type from material number, fallback to posting text."""
    if material and str(material).strip() in MATERIAL_FUEL_MAP:
        return MATERIAL_FUEL_MAP[str(material).strip()]
    if posting_text:
        text_lower = str(posting_text).lower()
        for keyword, fuel in POSTING_TEXT_FUEL_KEYWORDS.items():
            if keyword in text_lower:
                return fuel
    return None


def _normalize_quantity(quantity: float, uom: str, fuel_type: str) -> tuple[float, str, bool]:
    """
    Convert quantity to emission-ready unit.
    Returns (normalized_value, normalized_unit, success).
    """
    uom_key = uom.lower().strip()

    # Natural gas — prefer m3 or kWh
    if fuel_type == 'natural_gas_m3':
        if uom_key in ('m3', 'cbm', 'ft3'):
            val, ok = normalize_to_m3(quantity, uom_key)
            return val, 'm3', ok
        if uom_key in ('kwh', 'mwh'):
            from core.unit_conversion import normalize_to_kwh
            val, ok = normalize_to_kwh(quantity, uom_key)
            return val, 'kWh', ok

    # Liquid fuels — convert to litres
    if uom_key in ('kg', 'lb', 'g', 't', 'to'):
        val, ok = normalize_to_kg(quantity, uom_key)
        # approximate density: diesel ~0.85 kg/L, petrol ~0.74 kg/L
        density = 0.85 if 'diesel' in fuel_type else 0.74
        return val / density, 'L', ok

    val, ok = normalize_to_litres(quantity, uom_key)
    return val, 'L', ok


def parse(file_bytes: bytes, filename: str, plant_lookup: dict) -> list[dict]:
    """
    Parse SAP flat file. Returns list of row result dicts:
    {
      row_number, raw_data, status, errors, warnings,
      activity_value, activity_unit, fuel_type, scope,
      posting_date, document_number, plant_code, cost_center, material_number
    }
    """
    results = []

    # Detect format
    try:
        if filename.lower().endswith('.xlsx') or filename.lower().endswith('.xls'):
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        else:
            # Try tab first, then semicolon
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), sep='\t', dtype=str, encoding='utf-8-sig')
                if df.shape[1] < 3:
                    df = pd.read_csv(io.BytesIO(file_bytes), sep=';', dtype=str, encoding='utf-8-sig')
            except Exception:
                df = pd.read_csv(io.BytesIO(file_bytes), sep=';', dtype=str, encoding='latin-1')
    except Exception as e:
        return [{'row_number': 0, 'raw_data': {}, 'status': 'FAILED',
                 'errors': [f'Cannot read file: {str(e)}'], 'warnings': []}]

    # Normalize column names
    col_remap = {}
    for col in df.columns:
        norm = _normalize_col(col)
        if norm in COLUMN_MAP:
            col_remap[col] = COLUMN_MAP[norm]
    df = df.rename(columns=col_remap)

    required = {'quantity', 'unit_of_measure'}
    missing_cols = required - set(df.columns)
    if missing_cols:
        return [{'row_number': 0, 'raw_data': {}, 'status': 'FAILED',
                 'errors': [f'Missing required columns: {missing_cols}'], 'warnings': []}]

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed, accounting for header
        raw = row.to_dict()
        errors = []
        warnings = []

        # --- Quantity ---
        qty_raw = str(raw.get('quantity', '')).strip().replace(',', '.')
        if not qty_raw or qty_raw in ('nan', ''):
            errors.append('Missing quantity')
            results.append({'row_number': row_num, 'raw_data': raw,
                            'status': 'FAILED', 'errors': errors, 'warnings': warnings})
            continue
        try:
            quantity = float(qty_raw)
        except ValueError:
            errors.append(f'Non-numeric quantity: {qty_raw}')
            results.append({'row_number': row_num, 'raw_data': raw,
                            'status': 'FAILED', 'errors': errors, 'warnings': warnings})
            continue

        if quantity <= 0:
            errors.append(f'Quantity must be positive, got: {quantity}')
            results.append({'row_number': row_num, 'raw_data': raw,
                            'status': 'FAILED', 'errors': errors, 'warnings': warnings})
            continue

        # --- Unit of measure ---
        uom = str(raw.get('unit_of_measure', '')).strip()
        if not uom or uom == 'nan':
            errors.append('Missing unit of measure')
            results.append({'row_number': row_num, 'raw_data': raw,
                            'status': 'FAILED', 'errors': errors, 'warnings': warnings})
            continue

        # --- Fuel type resolution ---
        material = str(raw.get('material_number', '')).strip()
        posting_text = str(raw.get('posting_text', '')).strip()
        fuel_type = _detect_fuel_type(material, posting_text)
        if not fuel_type:
            warnings.append(f'Unknown material/fuel for material={material}, text={posting_text[:50]}. Defaulting to diesel.')
            fuel_type = 'diesel'

        # --- Normalize quantity ---
        norm_qty, norm_unit, convert_ok = _normalize_quantity(quantity, uom, fuel_type)
        if not convert_ok:
            warnings.append(f'Unrecognised UoM "{uom}" — using raw value without conversion')

        # --- Date ---
        posting_date = _parse_date(str(raw.get('posting_date', '')))
        if not posting_date:
            warnings.append('Could not parse posting date')

        # --- Plant lookup ---
        plant_code = str(raw.get('plant_code', '')).strip()
        if plant_code and plant_code not in ('nan', '') and plant_code not in plant_lookup:
            warnings.append(f'Plant code "{plant_code}" not in lookup table')

        plant_info = plant_lookup.get(plant_code, {})
        facility = plant_info.get('facility_name', '')
        country = plant_info.get('country_code', 'GB')

        # --- Emission factor ---
        ef_data = EMISSION_FACTORS.get(fuel_type, EMISSION_FACTORS['diesel'])
        ef_value = ef_data['factor']

        # Map norm_unit to correct EF
        if fuel_type == 'natural_gas_m3' and norm_unit == 'kWh':
            ef_data = EMISSION_FACTORS['natural_gas_kwh']
            ef_value = ef_data['factor']

        co2e = norm_qty * ef_value

        # --- Suspicion checks ---
        status = 'OK'
        if warnings:
            status = 'SUSPICIOUS'
        if errors:
            status = 'FAILED'

        results.append({
            'row_number': row_num,
            'raw_data': raw,
            'status': status,
            'errors': errors,
            'warnings': warnings,
            'fuel_type': fuel_type,
            'scope': ef_data['scope'],
            'activity_value': round(norm_qty, 4),
            'activity_unit': norm_unit,
            'activity_description': f'{fuel_type.replace("_", " ").title()} — {plant_info.get("plant_name", plant_code)}',
            'emission_factor': ef_value,
            'co2e_kg': round(co2e, 4),
            'posting_date': posting_date.date() if posting_date else None,
            'document_number': str(raw.get('document_number', '')).strip(),
            'plant_code': plant_code,
            'cost_center': str(raw.get('cost_center', '')).strip(),
            'material_number': material,
            'facility_name': facility,
            'country_code': country,
        })

    return results
