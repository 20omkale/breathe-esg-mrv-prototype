# SOURCES.md — Research on Real-World Data Sources

For each source I document what the real-world format actually looks like, what I learned that changed how I designed the ingestion, what my sample data looks like and why, and what would break in production.

---

## Source 1: SAP Fuel Data (Scope 1)

### What I researched

SAP's Materials Management (MM) module tracks fuel through its inventory management layer. When a vehicle or generator gets filled from an on-site tank, an operator posts a "Goods Issue against Cost Center" in transaction MIGO with movement type 201. The fuel exits the storage location (the tank) and is charged to a cost center (the operational unit that consumed it).

The standard report for querying these movements is **MB51 (Material Document List)**. It's available in every SAP MM installation without any special configuration. The output is an ALV (ABAP List Viewer) grid that can be exported as a character-separated flat file.

I found SAP's official field documentation for MB51 through the SAP Help Portal. The relevant fields are:

| SAP Field | German Label | English Label | Meaning |
|---|---|---|---|
| MATNR | Materialnummer | Material Number | Internal material code |
| MAKTX | Materialbezeichnung | Material Description | Free-text description |
| MENGE | Menge | Quantity | The volume/mass |
| MEINS | Mengeneinheit (ME) | Unit of Measure | L, KG, M3, GAL |
| BUDAT | Buchungsdatum | Posting Date | When it was recorded in SAP |
| BLDAT | Belegdatum | Document Date | Physical document date |
| WERKS | Werk | Plant | Which facility |
| KOSTL | Kostenstelle | Cost Center | Which operating unit consumed it |
| BWART | Bewegungsart | Movement Type | 201 = GI for cost center |

The material description field (MAKTX) is a free-text field filled by the company's MM administrators. It does not follow a standard — "Diesel HSD", "High Speed Diesel", "HSD Grade", and "Motor Fuel - Diesel" are all real examples I've seen referenced in SAP configuration guides. This is why my parser detects fuel type from keywords rather than expecting an exact string match.

### What I learned that changed the design

1. **Language of export depends on the SAP system's logon language setting.** German-headquartered multinationals often run SAP in German globally, so Indian subsidiaries export German column headers. My parser handles both.

2. **Units are not standardised across installations.** Most Indian SAP configs use L (litres), but bulk diesel deliveries to large tanks are sometimes recorded in M3 (cubic metres). CNG is always in KG.

3. **The date in MB51 is the posting date (BUDAT), not the physical delivery date.** Posting date can lag the actual delivery by 2–5 days if the operator is slow to enter the goods receipt. For monthly emissions reporting this is generally acceptable, but for precise period attribution it matters.

### What my sample data looks like and why

My sample file (`Test_Data/sap_fuel.csv`) uses the actual German field names from MB51 — MAKTX, MEINS, BUDAT, WERKS, KOSTL — because that's what an Indian subsidiary of a German company would actually export. Dates are in DD.MM.YYYY format.

I included:
- Rows in both L and KG (for CNG) and one row in M3 (bulk diesel) to test unit normalisation
- A row with a quantity of 12,500L surrounded by rows averaging ~2,000L — this is the intentional outlier that triggers the SUSPICIOUS flag
- A final row with a blank quantity marked as "GR pending" — this is the intentional parse failure that demonstrates per-row error tracking

### What would break in production

- **Plant-to-site mapping**: The WERKS field gives you a plant code like "MP01", not "Mumbai Operations Plant." You'd need a separate lookup table mapping plant codes to geographic locations for accurate site-level reporting.
- **Material code lookup**: Companies use internal material numbers (MATNR) like "FUEL-HSD-001" that mean nothing without SAP's material master. The description field is more useful but inconsistent.
- **Multiple company codes**: Large companies have multiple BUKRS (company codes) in a single SAP system. You'd need to filter by company code to avoid mixing entities.

---

## Source 2: Utility Electricity Data (Scope 2)

### What I researched

I looked at what portal CSV exports from Indian electricity utilities actually contain. I checked BESCOM (Bengaluru), MSEDCL (Maharashtra), TSSPDCL (Telangana), and KSEB (Kerala) — the four most common utilities for Indian commercial and industrial clients.

Common fields across all of them:
- Account number and meter ID (not the same — one account can have multiple meters)
- Bill period start and end dates (explicitly stated, not implied from month)
- kWh units consumed
- Reactive energy (kVAh) — relevant for power factor penalty calculations
- Maximum demand (kW) — part of HT/LT tariff structure
- Read type — actual or estimated
- Tariff code — determines the rate schedule

What's notably absent from most portal exports: the actual rupee amounts broken out by component. You usually get a total bill amount but not the itemised demand charges, energy charges, and taxes. I left financial data out of the model entirely — mixing billing amounts into a carbon database is a privacy and audit boundary issue.

### What I learned that changed the design

The key insight: **billing periods almost never align with calendar months.**

BESCOM meter reading cycles are typically 27–33 days, starting on different dates for different feeder routes. A company with 3 meters on 3 different reading cycles might get bills with periods like:
- Meter 1: Dec 20 – Jan 22 (33 days)
- Meter 2: Dec 15 – Jan 18 (34 days)
- Meter 3: Jan 5 – Feb 3 (29 days)

If you just use the bill date as the activity date, you'll have all three assigned to January, but their consumption spans parts of December and February too. For monthly emissions reporting this introduces systematic error.

My parser uses the midpoint of the billing period as the activity date, which distributes the consumption more accurately across months without requiring interval data.

### What my sample data looks like and why

My sample file has 15 rows across 3 meters at 3 sites (HQ Bangalore, Mumbai warehouse, Pune factory). Billing periods are explicitly stated with start and end dates, and they don't line up with month boundaries. Row 6 is marked `ESTIMATED` — this is the automated flag for the analyst.

The `DG_Supplement_kWh` column represents diesel generator supplemental consumption, which is common in Indian commercial buildings. I included it as a column but the current parser ignores it — in production this would need to feed into Scope 1 (it's direct combustion of diesel), but getting the meter-level DG attribution right is complex enough to warrant its own ingestion flow.

### What would break in production

- **Estimated billing corrections**: The utility sends a corrected bill the following month. If the analyst approves the estimated bill and then the corrected read comes in, you've double-counted. The flag helps, but a real solution would need the system to look for a correction row and prompt the analyst to void the original.
- **Tariff-based demand charges**: HT (High Tension) consumers pay demand charges based on contracted maximum demand. These affect the total bill but not the kWh consumed. The current model only tracks consumption, not cost.
- **Multiple utilities per site**: Large factories sometimes have both state grid supply and a captive solar plant. The portal exports won't automatically separate green and brown power. You'd need meter-level tagging for Scope 2 market-based vs. location-based reporting.

---

## Source 3: Corporate Travel Data (Scope 3, Category 6)

### What I researched

I looked at both Concur and Navan. Concur is dominant in Indian enterprise; Navan is growing but mostly in tech companies. For a construction company, Concur is the realistic assumption.

Concur offers several export formats. The relevant one for emissions is the **Standard Accounting Extract (SAE)** — a fixed-column CSV that finance teams use for expense reimbursement. It's available to every Concur customer.

Key fields in the SAE relevant to emissions:
- Expense type (Air Travel, Hotel, Car Rental, Taxi, Train, Meals, etc.)
- Transaction date
- Origin and destination (for air travel) — city names or IATA codes depending on Concur configuration
- Amount and currency
- Cabin class (if the company's expense policy captures it)

What's not in the SAE: distance. Concur does not calculate or store distances. This is stated explicitly in Concur's API documentation — the Travel itinerary API has routing data, but the Expense SAE does not.

I also read the GHG Protocol Scope 3 Calculation Guidance (v1.4, 2013, Category 6) and DEFRA's 2024 guidance on aviation emission factors. Two things came out of that research:

1. The DEFRA aviation factors (Table 10) include a radiative forcing (RF) multiplier. RF accounts for the warming effect of contrails and other non-CO2 impacts at high altitude. DEFRA says the RF multiplier is approximately 1.9× the CO2-only figure for long-haul flights. I used the factors with RF included because the GHG Protocol recommends it.

2. The short-haul vs. long-haul split matters for the factor. DEFRA uses different factors for flights under 1500km and over 1500km. My parser checks the computed distance against this threshold to select the right factor.

### What my sample data looks like and why

My sample file uses IATA airport codes (BOM, DEL, LHR, SIN, etc.) instead of pre-computed distances, because that's what a real Concur export contains. The parser looks up the distance from the IATA pair table built into the ingestion code.

Trip TR-2026-006 has `Legs=2` — this is the intentional multi-leg flag case. The analyst needs to manually verify per-leg cabin classes in the Concur trip report before approving it.

Hotel and ground transport rows are mixed into the same file because that's how Concur exports work — one file has all expense types together, not separate files per category.

### What would break in production

- **Routes not in the lookup table**: My airport pair table covers common India domestic routes and a handful of international routes. Any route not in the table causes a parse error. In production this would need to call a distance API (OpenFlights, Amadeus, or at minimum a full airport coordinates database with haversine computation) rather than a hardcoded lookup.
- **Multi-leg flights**: A single Concur row for a multi-stop trip cannot be correctly attributed to a single emission factor. The Concur Travel itinerary API has per-leg data, but the SAE does not. This is a fundamental limitation of the export format.
- **Currency for hotel nights**: Hotels are billed in local currency. Some Concur configurations report nights as a count, others report only the amount. My parser uses the `Nights` field — if it's absent, it defaults to 1, which will be wrong for any multi-night stay that doesn't have the nights count explicitly exported.
- **Personal vs. business travel**: Concur doesn't tag whether a trip was personal or business — that's determined by the expense report category. If an employee submits personal expenses through the same system, they'd need to be filtered at the expense report level before the SAE is exported.