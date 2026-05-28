# Sources

For each data source: what I researched, what I learned, what the sample data looks like, and what would break in a real deployment.

---

## Source 1: SAP Fuel & Procurement

### What I researched

SAP stores procurement transactions in several tables:
- `EKKO` — purchasing document header (vendor, company code, date)
- `EKPO` — purchasing document line items (material, quantity, unit, plant)
- `MSEG` — material document segments (goods movements, includes movement type)
- `MARA` / `MARC` — material master data

Movement type `261` in MSEG is a goods issue to a production order — the standard record for fuel consumption drawn from stock. Movement type `101` is a goods receipt. For a sustainability context, we want 261 (consumption), not 101 (purchase).

SE16N is SAP's general table browser available to any user with the transaction code. A Basis admin can configure a scheduled background job to export table data to a flat file on the SAP application server, which is then FTP'd or emailed. This is the most common manual integration pattern for mid-size SAP customers.

**German headers:** In a German-language SAP system, the column headers in an SE16N export appear in German. `Werk` = Plant, `Menge` = Quantity, `Maßeinheit` = Unit of Measure, `Buchungsdatum` = Posting Date, `Belegdatum` = Document Date, `Lieferant`/`Kreditor` = Vendor, `Material` = Material number. I handle all of these by building a bidirectional column alias map in the parser.

**Units:** SAP stores quantities in the ordering unit, which may not match the base unit. A diesel purchase might be ordered in `TO` (metric ton) while the material master stores it in `L` (litres). The conversion between ordering and base unit is in table `MARM`. Without access to `MARM`, we have to handle the most common units and flag the rest: `L` (litre), `KG` (kilogram), `M3` (cubic metre), `TO` (metric ton → convert at 1000kg/to → 1000 litres for diesel at ~0.835 kg/L density).

### What the sample data looks like

`backend/sample_data/sap_fuel_export.txt` is a tab-delimited flat file with:

- 46 rows covering one fiscal quarter
- A mix of diesel (L), natural gas (M3), and LPG (KG)
- Plant codes `1000` (Manchester), `1100` (Leeds), `2000` (Hamburg), and `9999` (intentionally unknown — no PlantLookup entry)
- One row with zero quantity (a reversal posting, common in SAP)
- One row with an unknown unit (`GAL` — US gallon, not in our mapping)
- German column headers: `Buchungsdatum`, `Werk`, `Menge`, `Maßeinheit`

The intentional edge cases (unknown plant, unknown unit, zero qty) test the SUSPICIOUS vs. FAILED logic.

### What would break in a real deployment

1. **The export is not standardized.** Two SAP customers rarely export the same column set from SE16N. One adds cost center, another removes document type. The parser handles ~20 column variants but will silently miss any unknown column.

2. **Unit conversion without MARM.** If a client orders fuel in ordering units different from base units, and we don't have MARM to resolve the conversion, we'll compute wrong emission values. The parser flags unknown units as FAILED, but a plausible-looking unit in the wrong context would produce wrong results silently.

3. **Reversal postings.** SAP uses negative-quantity rows to reverse previously posted consumption. Our parser treats negative quantities as SUSPICIOUS. In reality they should be matched and netted against the positive posting. Without document number cross-referencing this is ambiguous.

4. **Plant code collisions.** If a client has subsidiaries using different plant code namespaces (common in M&A), `1000` might mean two different facilities.

---

## Source 2: Utility Electricity

### What I researched

UK electricity billing is governed by the Distribution Network Operator (DNO) structure. Each metered supply point has an MPAN (Meter Point Administration Number) — a 13-digit number that is the unique identifier for the meter, not the account.

I looked at CSV export formats from:
- **E.ON Business Portal** — exports with columns: Account Number, MPAN, Site Name, Period From, Period To, Opening Read, Closing Read, Units, Rate (p/kWh), Amount (£)
- **British Gas for Business** — similar structure, adds a "Read Type" column (Actual/Estimated)
- **Stark** (multi-utility broker) — adds a Site Reference column and supports multi-site CSV aggregations

Smart meters (under the UK SMETS2 programme) are now mandatory for new commercial supplies. HH (half-hourly) metering for > 100 kW connections gives 48 readings per day, exported as a separate format entirely. I handle the simpler monthly/quarterly billing export, not HH data.

**Billing period misalignment:** Utility billing periods are set by the meter read schedule, not calendar months. A December bill might cover 23 Nov – 28 Dec (35 days). Our parser checks for period > 92 days (suspicious) and end < start (failed).

**MPAN validation:** The 13-digit MPAN has a check structure (the top line and bottom line encode DNO code, meter type, and serial). I implement the basic 13-digit format check. Full check digit validation requires the check digit algorithm which I didn't implement — it would add correctness but the top-line check is what utility portals themselves validate.

### What the sample data looks like

`backend/sample_data/utility_electricity.csv` contains:

- 26 rows across 4 meter points (different MPANs)
- Two sites: Manchester HQ, Leeds Warehouse
- Mix of actual and estimated reads (one estimated → SUSPICIOUS)
- One row where current reading < previous reading (meter rollover → SUSPICIOUS)
- One row with a kVA demand charge rather than kWh consumption (flagged — cannot compute emissions)
- One MPAN with 12 digits instead of 13 (invalid → SUSPICIOUS)
- Billing periods ranging from 28 to 35 days

### What would break in a real deployment

1. **Half-hourly data.** Any client on HH metering will have ~35,000 rows per meter per year. Our current approach parses one row per billing period. HH requires aggregation before emission calculation and a completely different data model for the readings table.

2. **Reactive power and power factor.** Some utility exports include kVArh (reactive energy) alongside kWh. We ignore these — they're relevant for power quality reporting but not for GHG accounting.

3. **Multi-rate tariffs.** Economy 7 and similar day/night tariffs split consumption into multiple rows with different rates in the same billing period. Our parser sums them as separate period rows, which double-counts the emission factor application.

4. **Estimated reads not resolved.** An "estimated" read in one period is corrected in the next. Our parser flags estimated reads as SUSPICIOUS but doesn't link consecutive reads to reconcile the correction.

---

## Source 3: Corporate Travel (Concur)

### What I researched

SAP Concur is the dominant platform in enterprise travel expense management. Concur's admin reporting tool produces CSV exports via the "SAE" (Standard Accounting Extract) format. I read the Concur SAE specification documentation and several third-party integrations.

Key columns in the relevant expense types:
- `Expense Type Name` — "Airfare", "Hotel", "Car Rental", "Train", "Taxi"
- `From City` / `To City` (often free text, inconsistent)
- `From Airport Code` / `To Airport Code` (IATA, present only for air)
- `Number of Nights` (hotel)
- `Distance` / `Distance Unit` (sometimes present for ground transport, often absent)
- `Department` / `Cost Center`
- `Travel Date`
- `Amount`, `Currency`

**The airport code problem:** Concur sometimes gives IATA codes, sometimes city names, sometimes neither. I use IATA codes as the primary path and fall back to a warning flag when codes are missing or invalid.

**Radiative forcing for aviation:** DEFRA 2024 guidance recommends an uplift factor of 1.9x on CO₂ emissions from flights to account for non-CO₂ warming effects at altitude (contrails, NOx). I apply this by default. Some reporting frameworks exclude it.

**Hotel emission factors:** DEFRA provides factors per hotel room night by region (UK, Europe, North America, etc.). Without a reliable destination country from the expense data, I use the UK factor as default and flag non-UK destinations as suspicious.

**Ground transport:** Concur logs car hire, taxi, and rail. Car hire is complex (vehicle type unknown → emission factor unknown). Taxi/rideshare is ambiguous (electric vs. petrol). I apply the DEFRA "average car" factor to car hire and rideshare rows and flag them as suspicious.

### What the sample data looks like

`backend/sample_data/concur_travel.csv` contains:

- 41 rows across 8 employees
- Mix of flights (domestic UK, European, transatlantic), hotels (UK and Europe), ground transport (taxi, car hire)
- Valid IATA codes (LHR, JFK, CDG, MAN) for most flights
- Two rows with invalid IATA codes (`XXX`, `ZZZ`) → FAILED
- One first-class transatlantic (higher emission factor, flagged to draw analyst attention)
- Hotel stays without destination country → SUSPICIOUS
- Ground transport rows → SUSPICIOUS (vehicle type unknown)

### What would break in a real deployment

1. **IATA code reliability.** Concur users sometimes type city names in the airport code field ("London" instead of "LHR"). Our parser will reject these as FAILED. A fuzzy city → IATA mapping would recover them but risks false positives.

2. **Personal car mileage.** When employees claim mileage for personal car use (not car hire), Concur records distance in miles or km and a reimbursement rate. The emission factor depends on engine size/fuel type which Concur doesn't capture. We don't handle this expense type at all — it's flagged as unknown and skipped.

3. **Indirect emissions from car hire.** The emission factor we apply assumes an average UK car. If a client's travel policy is "EV-only rental", applying the petrol average significantly overstates emissions. Without vehicle type from the rental company's data, we can't know.

4. **Multiple legs logged as one trip.** A three-leg transatlantic trip (MAN → LHR → JFK) might appear as two separate rows or as one row with MAN → JFK. The great-circle distance between MAN and JFK understates total distance by ~5-8%. Most expense tools log each booking separately, but consolidated booking tools may merge legs.

5. **Currency normalization for cost reporting.** All amounts are stored as-is. If the client runs expense reporting in multiple currencies (USD for US team, GBP for UK team), any cost-based analysis would require FX rates. We don't use cost data for emission calculations so this doesn't affect GHG accuracy, but it affects any future cost-per-tonne analysis.
