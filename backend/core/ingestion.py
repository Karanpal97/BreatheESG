"""
Ingestion orchestrator — ties together parsers with DB writes.
Called synchronously (no Celery needed for prototype).
"""

from django.utils import timezone
from .models import IngestionJob, RawRow, EmissionRecord, AuditLog, PlantLookup
from .parsers import sap_fuel, utility_electricity, travel_concur
import math


def _clean_raw(d: dict) -> dict:
    """
    Pandas uses float('nan') for empty CSV cells.
    PostgreSQL jsonb rejects NaN/Infinity — they are not valid JSON.
    Replace all float NaN / Inf values with None before storing.
    """
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = None
        else:
            cleaned[str(k)] = v
    return cleaned



def _build_plant_lookup(company) -> dict:
    """Build plant code → info dict for SAP parser."""
    return {
        p.plant_code: {
            'plant_name': p.plant_name,
            'facility_name': p.facility_name,
            'country_code': p.country_code,
        }
        for p in PlantLookup.objects.filter(company=company)
    }


def run_ingestion(job: IngestionJob, file_bytes: bytes, user) -> IngestionJob:
    """
    Main entry point. Parses file, writes rows to DB, updates job stats.
    Returns updated job.
    """
    job.status = IngestionJob.STATUS_PROCESSING
    job.save(update_fields=['status'])

    try:
        rows = _parse(job, file_bytes)
    except Exception as e:
        job.status = IngestionJob.STATUS_FAILED
        job.error_log = [str(e)]
        job.save(update_fields=['status', 'error_log'])
        return job

    count_ok = count_failed = count_suspicious = 0
    raw_rows_to_create = []
    emit_records_to_create = []
    audit_logs_to_create = []

    for row_data in rows:
        status_map = {'OK': RawRow.PARSE_OK, 'FAILED': RawRow.PARSE_FAILED, 'SUSPICIOUS': RawRow.PARSE_SUSPICIOUS}
        raw = RawRow(
            job=job,
            row_number=row_data['row_number'],
            raw_data=_clean_raw(row_data['raw_data']),   # ← sanitise NaN → None
            parse_status=status_map.get(row_data['status'], RawRow.PARSE_FAILED),
            parse_errors=row_data.get('errors', []),
            parse_warnings=row_data.get('warnings', []),
        )
        raw_rows_to_create.append((raw, row_data))

    # Bulk create raw rows
    RawRow.objects.bulk_create([r for r, _ in raw_rows_to_create])

    # Fetch created rows (need PKs for FK)
    created_raws = list(RawRow.objects.filter(job=job).order_by('row_number'))
    raw_map = {r.row_number: r for r in created_raws}

    for raw, row_data in raw_rows_to_create:
        raw_obj = raw_map.get(row_data['row_number'])

        if row_data['status'] == 'FAILED':
            count_failed += 1
            continue

        if row_data['status'] == 'SUSPICIOUS':
            count_suspicious += 1
            review_status = EmissionRecord.STATUS_FLAGGED
        else:
            count_ok += 1
            review_status = EmissionRecord.STATUS_PENDING

        # Determine period dates depending on source
        period_start = row_data.get('posting_date') or row_data.get('period_start')
        period_end = row_data.get('period_end') or period_start

        record = EmissionRecord(
            company=job.company,
            raw_row=raw_obj,
            job=job,
            scope=row_data.get('scope', 'SCOPE_3'),
            scope_3_category=row_data.get('scope_3_category', ''),
            source_type=job.source_type,
            source_document_ref=row_data.get('document_number') or row_data.get('source_document_ref') or row_data.get('account_number') or '',
            data_period_start=period_start,
            data_period_end=period_end,
            activity_value=row_data.get('activity_value', 0),
            activity_unit=_map_unit(row_data.get('activity_unit', 'L')),
            activity_description=row_data.get('activity_description', ''),
            emission_factor=row_data.get('emission_factor', 0),
            emission_factor_source=row_data.get('emission_factor_source', 'DEFRA 2024'),
            co2e_kg=row_data.get('co2e_kg', 0),
            facility_name=row_data.get('facility_name', ''),
            plant_code=row_data.get('plant_code', ''),
            cost_center=row_data.get('cost_center', ''),
            country_code=row_data.get('country_code', ''),
            department=row_data.get('department', ''),
            review_status=review_status,
        )
        emit_records_to_create.append((record, raw_obj, row_data))

    EmissionRecord.objects.bulk_create([r for r, _, _ in emit_records_to_create])

    # Write audit logs for created records
    created_records = list(EmissionRecord.objects.filter(job=job).select_related('raw_row'))
    for rec in created_records:
        AuditLog.objects.create(
            emission_record=rec,
            user=user,
            action=AuditLog.ACTION_CREATED,
            new_values={
                'scope': rec.scope,
                'activity_value': str(rec.activity_value),
                'activity_unit': rec.activity_unit,
                'co2e_kg': str(rec.co2e_kg),
                'review_status': rec.review_status,
            },
        )

    # Update job stats
    job.row_count_total = len(rows)
    job.row_count_ok = count_ok
    job.row_count_failed = count_failed
    job.row_count_suspicious = count_suspicious
    job.status = IngestionJob.STATUS_DONE
    job.save(update_fields=[
        'row_count_total', 'row_count_ok', 'row_count_failed',
        'row_count_suspicious', 'status'
    ])

    return job


def _parse(job: IngestionJob, file_bytes: bytes) -> list[dict]:
    if job.source_type == IngestionJob.SOURCE_SAP:
        plant_lookup = _build_plant_lookup(job.company)
        return sap_fuel.parse(file_bytes, job.original_filename, plant_lookup)
    elif job.source_type == IngestionJob.SOURCE_UTILITY:
        return utility_electricity.parse(file_bytes, job.original_filename)
    elif job.source_type == IngestionJob.SOURCE_TRAVEL:
        return travel_concur.parse(file_bytes, job.original_filename)
    else:
        raise ValueError(f'Unknown source_type: {job.source_type}')


def _map_unit(unit_str: str) -> str:
    """Map parser unit strings to EmissionRecord.UNIT_* choices."""
    mapping = {
        'L': 'L', 'litre': 'L', 'litres': 'L',
        'kWh': 'kWh', 'kwh': 'kWh',
        'kg': 'kg', 'KG': 'kg',
        'km': 'km', 'KM': 'km',
        'nights': 'nights',
        'pkm': 'pkm',
        'm3': 'm3', 'M3': 'm3',
    }
    return mapping.get(unit_str, unit_str)
