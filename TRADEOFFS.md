# Tradeoffs

Three things I deliberately did not build, and why.

---

## 1. Market-based Scope 2 accounting

**What it is:**
The GHG Protocol allows two methods for Scope 2 (purchased electricity) emissions:

- **Location-based:** Uses the average emission intensity of the national grid. Simple. One number from DEFRA per year.
- **Market-based:** Uses the emission factor of the specific electricity product the company has contracted for. If a company buys 100% renewable electricity via a Power Purchase Agreement (PPA) or Renewable Energy Guarantee of Origin (REGO) certificates, their market-based Scope 2 can be reported as zero.

Many enterprise clients — particularly those with net-zero commitments — report both and use market-based as their primary figure.

**Why I didn't build it:**
Market-based accounting requires supplier-specific emission factor data, residual mix factors (for the grid portion not covered by certificates), and documentation of the contractual instruments (PPA, REGOs). This is a data collection problem, not a parsing problem. The model schema supports it (the `emission_factor_source` field can hold any string, and a second record per meter could carry the market-based figure), but building the UI and ingestion pathway for certificate documentation would triple the scope.

**What I'd need to do it properly:**
A new `ContractualInstrument` model, a UI for analysts to attach PPAs/REGOs to meters, and a separate aggregation path in the dashboard for market-based totals. DEFRA publishes a spreadsheet of supplier emission factors annually — that would replace `GRID_EF` for market-based records.

---

## 2. Async ingestion (Celery/background workers)

**What it is:**
Parsing large files (10,000+ row SAP exports, multi-year utility histories) synchronously blocks the Django view thread. The correct production architecture is to immediately return a `job_id` and process the file in a background task queue (Celery + Redis), polling or using WebSockets to update the frontend.

**Why I didn't build it:**
The sample files and realistic prototype data are in the hundreds-of-rows range, where synchronous parsing completes in under 2 seconds. Adding Celery requires:
- A Redis or RabbitMQ broker (additional infrastructure)
- A Celery worker process (separate Render service)
- A result backend
- Task retry/failure handling
- Frontend polling or WebSocket integration

This is 2–3 days of additional engineering for zero user-visible benefit at prototype scale.

**The existing model is ready for it:**
`IngestionJob` already has `status: PENDING → PROCESSING → DONE | FAILED`. Moving `run_ingestion()` from the view into a Celery task requires changing three lines of code. The infrastructure work is the real cost, not the application logic.

**When this becomes critical:**
A single large client's annual SAP export can be 50,000+ line items. At that scale, synchronous parsing would time out on any PaaS with a 30-second request limit. Celery is the right answer — just not for a 4-day prototype.

---

## 3. Role-based access control (RBAC) beyond Analyst/Admin

**What it is:**
A fuller RBAC system would include roles like:
- **Data Uploader** — can upload files but not approve records
- **Reviewer** — can approve/reject but not edit activity values
- **Auditor** — read-only access to approved records only
- **Company Admin** — can manage users within their tenant but not across tenants
- **Platform Superadmin** — Breathe ESG staff access

The current system has only two roles: ANALYST (can do everything) and ADMIN (same, plus user creation).

**Why I didn't build it:**
The brief asks for a prototype to show to a PM and potentially to clients. The approval workflow — upload → review → approve/reject → lock — is the core loop. Spending time on permission matrices that the PM hasn't defined would be premature.

More concretely: I don't know what the actual operational split is at Breathe ESG. Is approval always a single person? Is there a four-eyes rule (two analysts must approve)? Can an uploader also be a reviewer? These questions need answers before designing RBAC. Building a system now would almost certainly be wrong in the details and need to be torn out.

**The risk I'm accepting:**
An ANALYST can currently upload a file and then approve their own records. In an audit context, this is a segregation of duties problem. For a prototype this is acceptable. For production it means adding at minimum a check that `reviewed_by != uploaded_by`.

**How I'd extend it:**
Django has a solid permission framework built in. Adding object-level permissions via `django-guardian` or a custom `Permission` model with `company`-scoped role assignments would be the right approach. The `User.role` field would become a ManyToMany to a `Role` model with a `permissions` JSON field.
