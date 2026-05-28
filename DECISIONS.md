# Decisions

Every significant ambiguity I hit, what I chose, and why.

---

## SAP Export Format: Flat file over IDoc / OData

**The ambiguity:** SAP exposes data through IDocs (XML-based message format), OData services (REST-like), BAPIs (function module calls), and flat-file exports from SE16N or FAGLL03.

**What I chose:** Tab-delimited flat file export from SE16N (General Table Display), the direct table dump format.

**Why:**
- IDocs require an active SAP integration middleware (SAP PI/PO or BTP Integration Suite). No client will give an intern-level prototype direct IDoc access — the security review alone takes months.
- OData requires RFC connections and is typically not exposed externally without a custom VPN or API gateway setup.
- Flat file via SE16N is what sustainability teams actually do. They ask the SAP Basis team to run a dump of EKKO (purchasing headers), EKPO (line items), and movement type 261 entries from MSEG. This is the realistic data shape: a tab-separated export with German column headers in some configurations (Werk = Plant, Menge = Quantity, Maßeinheit = Unit of Measure).

**What I'd ask the PM:**
- Do clients have an SAP Basis admin who can automate this export, or is this a one-time manual dump?
- Are we getting purchase order data (EKKO/EKPO), goods movements (MSEG), or both?
- What SAP version? S/4HANA vs. ECC 6.0 have different field structures.

**What I ignored from SAP reality:**
- GR/IR clearing accounts — we only process confirmed goods receipts (movement type 261)
- Multi-currency POs — all amounts treated as informational, not used for emissions
- Batch/serial number traceability
- Cross-company code postings

---

## Utility Electricity: Portal CSV export over PDF or API

**The ambiguity:** Facilities teams receive electricity data as PDF bills in the post, portal CSV exports, or (for large commercial customers) via APIs like EDF's DES API.

**What I chose:** Portal CSV export.

**Why:**
- PDF parsing is fragile and varies dramatically between utility providers. It requires OCR or layout-aware PDF parsing libraries. For a 4-day prototype this is the wrong place to spend time.
- Utility APIs exist but require client registration per utility account, OAuth flows, and are UK-specific (half-hourly AMR data). This is solvable in production but not for a prototype.
- Portal CSV is what every facilities manager I looked up on LinkedIn actually does: log in to the Stark/E.ON portal, select date range, download CSV, attach to email. It's the realistic mode. The UK smart meter rollout has made this nearly universal.

**Format research:**
I looked at E.ON Business, British Gas for Business, and Stark (multi-site utility broker) export formats. All share a common shape: account number, MPAN (Meter Point Administration Number), site address, billing period start/end, previous/current reading, units consumed, tariff rate, total amount. The MPAN is 13 digits — I implemented validation for this.

**Non-aligned billing periods:**
Utilities bill to meter read dates, not calendar months. A "December" bill might cover 23 Nov – 28 Dec. I handle this by storing `data_period_start` and `data_period_end` explicitly and flagging periods > 92 days as suspicious.

**What I'd ask the PM:**
- Do we need to handle kVA demand charges as well as kWh consumption? (I currently warn on kVA rows but can't assign emissions.)
- Are clients on half-hourly metering (HH) or settled monthly? HH would give us 48 readings per day per meter which changes the data volume assumption by ~100x.

---

## Corporate Travel: File upload over Concur API pull

**The ambiguity:** Concur exposes a full REST API (SAE standard). We could pull data programmatically. Alternatively, Concur admins can export reports as CSV.

**What I chose:** CSV file upload (Concur admin expense export).

**Why:**
- The Concur API requires OAuth 2.0 with company-specific client credentials. Getting those credentials requires a request to the client's IT security team. In practice this takes 2–6 weeks.
- Concur's SAE format is well-documented and every Concur admin knows how to run a standard expense report.
- This also generalises: the same CSV pipeline handles Navan (formerly TripActions), Cytric, and Egencia exports which follow similar shapes.

**Emission factor methodology for flights:**
Flights present a specific problem: Concur gives you departure and arrival airport codes (IATA), not distances. I resolved this by:
1. Using a bundled lookup of ~3,500 airport coordinates (lat/lon) from `airport_coords.py`
2. Computing great-circle distance via the Haversine formula
3. Applying a radiative forcing uplift multiplier of 1.9x (DEFRA 2024 guidance for high-altitude effects)
4. Applying DEFRA 2024 factors per passenger-km by class (economy short/long haul, premium economy, business, first)

Short haul is defined as < 3,700 km (roughly the great-circle limit for intra-European routes), matching DEFRA's own threshold.

**What I ignored from Concur reality:**
- Mileage reimbursement claims (personal car travel) — different emission factor, different field
- Per-diem meal expenses — no emissions
- Foreign currency conversion for cost fields
- Approval status filtering (I ingest all rows regardless of expense claim status)

**What I'd ask the PM:**
- Should we ingest only approved/reimbursed expenses, or everything submitted?
- Do clients want car hire emissions separately from flights?

---

## Synchronous ingestion over async (Celery)

**The ambiguity:** Large files (10,000+ rows) would block a Django view thread for many seconds during parse.

**What I chose:** Synchronous parsing in the request-response cycle.

**Why:** For a prototype with files in the hundreds-of-rows range, this is fine. Adding Celery requires a Redis/RabbitMQ broker, worker processes, a result backend, and retry logic — significant operational complexity with no benefit at prototype scale.

**What I'd change at production scale:** Move `run_ingestion()` to a Celery task. The `IngestionJob` model already has a `status` field with PENDING → PROCESSING → DONE lifecycle, exactly what's needed to poll from the frontend. The code change would be minimal.

---

## Shared schema multi-tenancy over schema-per-tenant

**What I chose:** All tenant data in a single PostgreSQL schema, with `company` FK on every relevant table.

**Why:** Schema-per-tenant (separate PostgreSQL schema per client) gives stronger isolation but requires schema creation on onboarding, separate migration runs per tenant, and schema-aware connection pooling. For ≤ 20 clients this complexity is not justified.

**The risk I'm accepting:** A bug in the API layer's company filter could leak one client's data to another. Mitigated by: (a) always filtering by `request.user.company`, not by a URL parameter the user controls, and (b) every queryset hitting the DB is scoped to company at the ORM level.

---

## Flat file storage for uploaded files over S3

**What I chose:** Django's `FileField` with local disk storage (`/media/uploads/`).

**Why:** For local dev and prototype this is simplest. On Render (ephemeral file system) uploaded files will not persist across deploys. For production this should be replaced with `django-storages` + S3.

This is documented in TRADEOFFS.md.

---

## DEFRA 2024 as the emission factor source

**The ambiguity:** Multiple emission factor databases exist — DEFRA (UK), EPA (US), IPCC AR6, IEA.

**What I chose:** DEFRA 2024 conversion factors throughout.

**Why:** Breathe ESG appears UK/EU oriented based on the brief. DEFRA publishes annual conversion factors in a standard spreadsheet format, covering UK grid electricity, vehicle fuels, flights by class and haul, and hotels — exactly our three source types. It is the standard used by UK SECR-compliant reporting.

**Limitation:** The grid electricity factor I'm using is the UK national average (location-based). Market-based Scope 2 accounting (using supplier-specific renewable certificates) requires a different methodology. See TRADEOFFS.md.
