# Data Model

## Overview

The model is designed around one central constraint: **an emission record must be traceable back to its exact source byte, with every change logged, by multiple clients on the same platform.** This drove the structure more than any other consideration.

---

## Entity Relationship Summary

```
Company
  └── User (many)
  └── IngestionJob (many)
       └── RawRow (many)          ← exact source data, never mutated
            └── EmissionRecord    ← normalized, editable, one-to-one with RawRow
                 └── AuditLog (many)
EmissionFactor (global lookup)
PlantLookup (per Company)
```

---

## Tables

### `Company`
The top-level tenant. Every piece of data — jobs, records, plant lookups — is scoped to a company. Users belong to exactly one company. There is no cross-company data access anywhere in the API layer.

```python
id          UUIDv4 PK
name        str
slug        str (unique)
created_at  datetime
```

Why UUID PKs throughout: sequential integer IDs leak record counts across tenants if an API ever gets misconfigured. UUIDs are opaque by default.

---

### `User`
Extends Django's `AbstractUser`. Adds `company` FK and `role` (ANALYST | ADMIN).

The reason for extending AbstractUser rather than using a separate Profile model is simplicity — there are only two fields to add, and keeping authentication and authorization in the same model avoids a join on every permission check.

Role is flat (not RBAC) by design — see TRADEOFFS.md.

---

### `IngestionJob`
Represents one file upload. Created before parsing starts, updated as parsing completes.

```python
id                  UUIDv4 PK
company             FK → Company
source_type         enum: SAP_FUEL | UTILITY_ELECTRICITY | TRAVEL_CONCUR
uploaded_by         FK → User (SET_NULL on delete)
uploaded_at         datetime (auto)
original_filename   str          # preserved for audit display
file                FileField    # stored in /media/uploads/YYYY/MM/
status              enum: PENDING | PROCESSING | DONE | FAILED
row_count_total     int
row_count_ok        int
row_count_suspicious int
row_count_failed    int
parser_version      str          # e.g. 'sap_fuel_v1'
error_log           JSON         # top-level parse errors (file unreadable etc.)
```

`parser_version` matters because emission factors and parsing logic change. If we re-parse historical files, we need to know which logic produced which records.

---

### `RawRow`
**This is the source-of-truth layer.** Every row from every parsed file is written here exactly as parsed (the original dict from pandas), before any normalization. It is never updated after creation.

```python
id             UUIDv4 PK
job            FK → IngestionJob
row_number     int              # line number in source file
raw_data       JSON             # original row as key-value dict
parse_status   enum: OK | SUSPICIOUS | FAILED
parse_errors   JSON list        # e.g. ["Non-numeric consumption: 'N/A'"]
parse_warnings JSON list        # e.g. ["MPAN does not match 13-digit UK format"]
```

Why keep raw data separately from `EmissionRecord`? Two reasons:

1. **Immutability.** If an analyst edits an `EmissionRecord` (e.g. corrects a quantity), we must still have the original value. `RawRow.raw_data` is never touched after bulk_create.
2. **Failure visibility.** Rows that failed parsing have no `EmissionRecord`. They still exist in `RawRow` with their errors, so analysts can see what was rejected and why.

---

### `EmissionRecord`
The normalized, analyst-facing layer. One-to-one with a `RawRow` (only created for rows that parsed successfully or suspiciously — not for FAILEDs).

**GHG Classification**
```python
scope          enum: SCOPE_1 | SCOPE_2 | SCOPE_3
scope_3_category str  # e.g. 'Category 6: Business travel'
```

Scope is assigned by the parser, not the analyst, because it is deterministic from source type:
- SAP fuel → Scope 1 (direct combustion)
- Utility electricity → Scope 2 (purchased energy)
- Concur travel → Scope 3 (value chain)

`scope_3_category` follows the GHG Protocol category taxonomy.

**Activity Data (normalized)**
```python
activity_value        Decimal(18,4)
activity_unit         enum: L | kWh | kg | km | nights | pkm | m3
activity_description  str
```

Units are normalized at parse time. SAP may give quantities in litres, cubic metres, or kilograms — all are stored in their native normalized unit with the unit column set explicitly. We do not convert everything to a single unit because that would lose information and introduce rounding errors before the analyst has reviewed anything.

**Emission Calculation**
```python
emission_factor        Decimal(12,6)
emission_factor_source str           # e.g. 'DEFRA 2024 (UK Grid)'
co2e_kg                Decimal(18,4)
```

`co2e_kg = activity_value × emission_factor`. Both are stored, not just the result. This means if the emission factor is later found to be wrong, we can recalculate without re-parsing. The `emission_factor_source` string makes the provenance explicit.

**Location and Organizational Context**
```python
facility_name    str
plant_code       str    # SAP plant code, looked up via PlantLookup
cost_center      str
country_code     str
department       str    # Concur expense department
```

**Analyst Review Lifecycle**
```python
review_status   enum: PENDING_REVIEW | FLAGGED | APPROVED | REJECTED
reviewed_by     FK → User (nullable)
reviewed_at     datetime (nullable)
reviewer_note   text
is_locked       bool    # True after APPROVED — prevents further edits
edit_note       text    # analyst's note when editing activity_value
edited_by       FK → User (nullable)
```

The `is_locked` field is the audit gate. Once a record is approved and locked, the API refuses further PATCH operations. This is enforced in the view layer, not just the model, so it works even if someone bypasses the UI.

---

### `AuditLog`
Every state-changing action on an `EmissionRecord` creates an immutable log entry.

```python
id               UUIDv4 PK
emission_record  FK → EmissionRecord
user             FK → User (SET_NULL on delete — logs outlive users)
action           enum: CREATED | EDITED | APPROVED | REJECTED | FLAGGED | LOCKED
timestamp        datetime (auto)
old_values       JSON    # fields before change
new_values       JSON    # fields after change
note             text
```

`old_values` and `new_values` are populated on EDITED actions to make the diff reconstructable. For APPROVED/REJECTED, `note` contains the reviewer's reasoning.

---

### `EmissionFactor`
Global lookup table, not tenant-scoped. Loaded from DEFRA 2024 at setup.

```python
activity_type    str     # e.g. 'diesel', 'grid_uk', 'flight_economy_short'
factor_value     Decimal(12,6)
unit             str     # e.g. 'kg_co2e_per_litre'
source_dataset   str     # e.g. 'DEFRA 2024'
country_code     str
valid_from       date
valid_to         date
notes            text
```

Factors are looked up at parse time and the value is **copied into `EmissionRecord.emission_factor`**. We don't store a FK to `EmissionFactor` in the record. Reason: DEFRA updates factors annually. If we stored only a FK, a factor update would silently change historical CO₂e figures without creating an audit trail.

---

### `PlantLookup`
Maps SAP plant codes (e.g. `1000`, `DE01`) to human-readable facility names. Scoped to `Company` because plant codes are client-internal.

```python
plant_code     str
company        FK → Company
plant_name     str
country_code   str
facility_name  str
```

---

## Multi-tenancy

Implemented as shared schema / row-level isolation (not separate schemas per tenant). Every query in the API layer filters by `request.user.company`. This is enforced in the view layer.

**Why not schema-per-tenant?** For a prototype with N < 20 clients, the operational overhead of managing N PostgreSQL schemas outweighs the isolation benefit. The tradeoff would be revisited before any enterprise go-live.

---

## Scope 1/2/3 Categorization

| Source | Scope | GHG Protocol Reference |
|--------|-------|------------------------|
| SAP fuel / procurement | 1 | Direct emissions from owned/controlled sources |
| Utility electricity | 2 | Purchased electricity (location-based method) |
| Concur flights | 3, Cat. 6 | Business travel — air |
| Concur hotels | 3, Cat. 6 | Business travel — accommodation |
| Concur ground transport | 3, Cat. 6 | Business travel — ground |

---

## Unit Normalization

Each parser is responsible for converting raw source units to the normalized `activity_unit` enum before creating an `EmissionRecord`. The conversion factors are in `core/unit_conversion.py`. For SAP specifically, units arrive as SAP internal unit codes (e.g. `L` for litre, `KG` for kilogram, `M3` for cubic metre) which are mapped explicitly.

We do not convert everything to one unit (e.g. MJ equivalent) because:
- It would lose the original unit, making auditor review harder
- It would introduce systematic rounding errors across thousands of records
- DEFRA emission factors are given per native unit (per litre, per kWh, etc.)

---

## What this model does not handle

- Multiple emission factor methodologies per record (market-based vs. location-based for Scope 2)
- Target/budget tracking
- Partial period records (e.g. a company mid-year onboarding)
- Currency normalization for cost data

These are documented in TRADEOFFS.md.
