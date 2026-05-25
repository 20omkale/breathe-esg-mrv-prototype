# DECISIONS.md — Engineering Decisions and Resolved Ambiguities

Every decision below is something I genuinely had to figure out. For each one I explain what I chose, why, and what I would ask the PM if I had the chance.

---

## 1. SAP — which export format?

The assignment says to pick one of: IDoc, flat file, OData service, BAPI. I looked at all four.

**IDoc** (Intermediate Document) is SAP's EDI format for inter-system messaging. It's how SAP talks to other SAP systems or external partners. It's not what a sustainability lead would pull when they need fuel consumption data — it requires the ALE/EDI layer to be configured and isn't a standard reporting output.

**OData** (via SAP Gateway) is the modern REST interface to SAP. It's great for real-time integration, but it requires the SAP Gateway server to be activated and an OData service to be configured for the right data object. Many SAP installations, particularly older ERP 6.0 setups in manufacturing companies, don't have this configured for internal reporting data.

**BAPI** (Business Application Programming Interface) is a function module that can be called remotely. Same problem as OData — it requires custom development or a pre-existing integration layer.

**MB51 flat file** is what I chose. MB51 is the Material Document List transaction in SAP MM (Materials Management). You run it by plant, date range, and movement type, and export it directly from the ALV grid — no special configuration needed. Movement type 201 is "Goods Issue against Cost Center", which is how fuel consumption is recorded in SAP MM: the fuel tank is a storage location, and each fill of a vehicle or generator creates a 201 movement. Every SAP installation that uses MM for procurement and inventory will have this transaction available. The export is a character-separated flat file.

The complication I had to handle: SAP's display language. If the SAP system's logon language is German (common in multinational companies with German HQ), the column headers come out in German — `Menge` instead of `Quantity`, `BUDAT` instead of `Posting_Date`, `MAKTX` instead of `Description`. I built a field-name mapping table that handles both German and English column names so neither version requires manual renaming before upload.

The other complication: dates. German SAP configurations default to DD.MM.YYYY. English configurations use YYYY-MM-DD. My parser tries both formats.

**What I'd ask the PM:** What version of SAP are they running? ERP 6.0 or S/4HANA? S/4HANA has a much better OData layer — if they're on S/4HANA, switching to the Materials Management OData service would give us real-time pull instead of periodic file export, which is a significantly better architecture for a production system.

---

## 2. Utility data — which format?

I looked at three options:

**PDF bill parsing** — most utility bills in India are PDFs. Parsing PDFs reliably is hard. Different utilities have different layouts, and even the same utility sometimes changes its layout between billing cycles. I ruled this out — the failure rate on real-world PDF parsing is high enough to require a lot of manual cleanup, which defeats the purpose of the ingestion pipeline.

**Green Button XML** — Green Button is the US standard for utility data sharing, supported by ESPI (Energy Service Provider Interface). Most major US utilities offer it. In India, it's essentially absent. The client is Indian (ABC Construction), so this isn't applicable.

**Portal CSV export** — what I chose. Almost every Indian electricity utility's online portal has a "Download Usage" or "View Bills" option that exports a CSV or Excel file. The facilities team already uses this to manually track consumption — we're just formalising that process. This is the realistic path for 90% of Indian corporate clients right now.

The key insight from looking at real utility exports: billing periods don't align with calendar months. BESCOM, TSSPDCL, and MSEDCL all send bills based on meter reading dates, not calendar month ends. A bill might cover December 20 to January 22 — that's 33 days spanning two months. If you just use the bill end date as the activity date, your monthly totals will be off.

My parser uses the midpoint of the billing period as the activity date. This isn't perfect — consumption isn't uniformly distributed across the billing period — but it's more correct than using the end date, and it avoids the double-counting risk when a billing period crosses a month boundary.

Estimated reads are automatically flagged. When a utility can't access the meter (locked premises, etc.) they issue an estimated bill based on historical consumption. The corrected actual reading comes the following month. If both get approved, you double-count that electricity. The flag puts it in front of the analyst before that happens.

**What I'd ask the PM:** Does the facilities team download from a single utility portal, or do they pull from multiple (different utilities per site)? And does any site have automated meter reading (AMR) — if so, some utilities offer API access to interval data, which would be dramatically better than monthly CSV exports.

---

## 3. Corporate travel — which platform and format?

I looked at Concur and Navan (formerly TripActions).

**Navan's API** is more modern (REST, JSON) and better documented publicly. But our client is an enterprise construction company. Large Indian enterprises that were early adopters of travel management systems are almost universally on SAP Concur, not Navan. Navan's enterprise penetration in India is still relatively low.

**Concur's Standard Accounting Extract (SAE)** is what I chose. The SAE is Concur's primary export format — it's a fixed-column CSV that finance teams use for expense reimbursement reconciliation. It's available to every Concur customer without any special API access or configuration.

The critical thing I learned about Concur exports: they do not include distance. You get the origin and destination as city names or IATA airport codes, depending on the Concur configuration. The distance between those two points has to be computed externally.

For this prototype I built a lookup table of IATA airport pairs covering domestic Indian routes and common international routes for an Indian corporate client (BOM, DEL, BLR, MAA, HYD, CCU, DXB, LHR, SIN, JFK, FRA, CDG). Distances were calculated using the haversine formula from airport coordinates in the OurAirports dataset (CC0 licensed). For routes not in the table, the parser raises an error with the specific route, so the analyst knows exactly what's missing rather than getting a silent zero.

For emission factors, I used DEFRA 2024 Table 10 (Aviation) with radiative forcing included. The RF multiplier roughly doubles the climate impact of flying vs. CO2 alone — it accounts for contrail formation and other non-CO2 warming effects at altitude. The GHG Protocol Scope 3 Technical Guidance for Category 6 (Business Travel) recommends including RF, so I included it. The factor source is explicitly stored in the `EmissionFactor` table.

Multi-leg flights are flagged. A single Concur line item can represent a multi-stop itinerary — BOM to FRA to LHR — with one cabin class. If the passenger flew economy on the first leg and business on the second, the per-km factor for the whole journey will be wrong. I can't fix this from the export alone; I flag it so the analyst can verify the per-leg details in the Concur trip report.

Hotels use nights as the unit, with a GHG Protocol Scope 3 Category 6 average factor of 20.8 kgCO2e per hotel night (Asia-Pacific average). Ground transport (taxi, car, rail) uses DEFRA 2024 factors per km.

**What I'd ask the PM:** Does the client use Concur Travel and Concur Expense together, or just Expense? If they have Concur Travel, the itinerary data (with actual routing and leg-by-leg details) might be available via the Travel Search API, which would solve the multi-leg problem. If it's just Expense, we're stuck with the SAE format.

---

## 4. Emission factors — hardcoded vs. database vs. external API

External APIs like Climatiq offer real-time emission factor lookup. I didn't use one for a deliberate reason: API calls in the ingestion path add latency and an external failure point. If the Climatiq API is down when a client uploads a 500-row file, the entire ingestion fails. That's a bad trade-off for a prototype.

Hardcoded constants are worse — they're not auditable and they don't update.

The middle ground is the `EmissionFactor` table in the database. Factors are seeded from real published sources (DEFRA 2024, CEA Version 18) with full citations. They're versioned by `valid_from` date. When new factors are published, we add new rows. Old records are unaffected.

The specific sources and why I chose them:
- **DEFRA (UK)** for fuels and flights: Published annually with clear versioning, widely accepted in Indian ESG consulting as the reference source when national-specific factors aren't available, covers the widest activity type range.
- **CEA CO2 Baseline Database Version 18** for Indian grid electricity: India's grid is approximately 2× more carbon-intensive than the UK grid. Using DEFRA's UK electricity factor would understate Scope 2 by roughly 50%. The CEA factor is the correct choice for an Indian client.
- **GHG Protocol Scope 3 Calculation Guidance** for hotel stays: The GHG Protocol is the governing standard for Scope 3, Category 6 calculations. Their Asia-Pacific average of 20.8 kgCO2e per hotel-night is the appropriate reference in the absence of supplier-specific data.

---

## 5. Duplicate upload handling — append or upsert?

If someone uploads a corrected version of a file they already uploaded last month, what happens?

I went with append-only. The new upload creates a new `IngestionBatch` and new `EmissionRecord` rows. The analyst rejects the old records and approves the new ones. Old data is never deleted.

The alternative — upsert (match existing records and overwrite) — requires a reliable natural key to identify "the same activity." SAP document numbers could serve this purpose, but utility bills and travel expenses don't have a consistent unique identifier across exports. Building a deduplication key that works across all three source types would require more time than this sprint allows, and getting it wrong would be worse than not having it.

**What I'd ask the PM:** What's the expected frequency of re-uploads? If it's common (e.g. utilities re-issuing corrected bills is a normal part of their workflow), we'd need smarter deduplication. If it's rare, the analyst workflow of reject-old/approve-new is probably fine.

---

## 6. File upload vs. text paste

The original version accepted raw CSV text in a JSON body. That's not how file uploads work in practice — analysts have CSV files on their desktop, not clipboard-ready text. I switched to multipart file upload, which is the standard browser mechanism for file transfer. It also handles encoding correctly: the parser wraps the file in `TextIOWrapper` with `utf-8-sig` encoding, which strips the BOM that Excel and SAP sometimes add to CSV files.