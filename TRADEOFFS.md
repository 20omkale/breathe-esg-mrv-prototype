# TRADEOFFS.md — Three Things I Deliberately Did Not Build

The assignment asks for three things I chose not to build and why. Here are mine, with the exact consequence of each decision stated.

---

## 1. No background job processing (Celery + Redis)

**What I skipped:** Asynchronous task processing. In a production system, a file upload would immediately return a job ID, and the actual parsing would happen in a background worker (Celery is the standard for Django). The frontend would poll or use a websocket to check when the job completed.

**Why I skipped it:** Adding Celery requires a Redis or RabbitMQ broker, separate worker processes, and significantly more infrastructure configuration. On Render's free tier, running a web service, a worker, and a Redis instance simultaneously would require at least two paid services.

**The concrete consequence:** File uploads are synchronous. The HTTP request blocks until the entire file is parsed. For a 20-row test file this takes under a second. For a real SAP MB51 export covering a full year (which could have 2,000+ material movement lines), the request would take several seconds — potentially long enough to hit Render's 30-second timeout for free-tier web services.

**The threshold where this breaks:** In testing, the parser handles about 500 rows per second. Files under 300 rows are safe on the free tier. Anything over 1,000 rows should go to a background worker in production.

---

## 2. No authentication or role-based access control

**What I skipped:** A login system. There's no concept of user identity in the current app — any request to any endpoint is accepted without credentials.

**Why I skipped it:** Proper authentication in a multi-tenant system is more involved than it appears. You need: user registration, login/logout, session or JWT management, and — critically — the access control logic that ties a user to a specific company. An analyst for Company A should not be able to call `/api/records/?company_id=2` and see Company B's data. Implementing that guard correctly across every endpoint takes time that was better spent on the data model and source research.

**The concrete consequence:** The current system has no data isolation at the request level. Anyone with the API URL can query any company's data by changing the `company_id` parameter. The only reason this doesn't matter for the prototype is that it's a demo with a single test company.

**What production auth would need:** Django REST Framework's token authentication or a JWT library (djangorestframework-simplejwt), a User-Company membership model, and a custom permission class that checks the requesting user's company membership before every view executes.

---

## 3. Static emission factors — no support for Scope 3 Category 1 (purchased goods)

**What I skipped:** Economic input-output based emission factors for procurement data. The assignment mentions "procurement data" alongside fuel in the SAP source. Scope 3 Category 1 (Purchased Goods and Services) is what procurement data maps to.

**Why I skipped it:** Category 1 requires spend-based or activity-based factors that are completely different from the combustion and transport factors I built. Spend-based Category 1 uses economic input-output (EIO) models — you take procurement spend by category (steel, concrete, electrical equipment) and multiply by an industry-sector emission intensity factor from databases like USEEIO or Exiobase. These are multi-dimensional lookups: spend × sector × currency × geographic region → kgCO2e. Building even a basic version of that lookup correctly is a separate project.

**The concrete consequence:** The current system handles the fuel component of SAP data (movement type 201, Goods Issues for consumption) but ignores the procurement component (purchase orders, Goods Receipts). A complete Scope 3 inventory for a construction company would require Category 1 for materials like steel, cement, and aggregates — these are often the largest contributors to total footprint for construction firms, sometimes 10× larger than Scope 1 and 2 combined.

**What building this would require:** An EIO factor dataset (USEEIO for US, or a commercial equivalent for India), a procurement category taxonomy that maps SAP material groups to EIO sectors, and a spend normalisation layer that handles currency conversion. This is a research project in itself, not a weekend add-on.