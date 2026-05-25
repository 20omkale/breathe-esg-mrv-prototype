# MODEL.md — Data Model and Design Rationale

## The core challenge this model is solving

ESG data doesn't come from one place in a clean format. It comes from SAP exports, utility portals, and travel platforms, each with different shapes, different units, and different reliability levels. The model has to do a few things at once: normalize all of that into comparable kgCO2e figures, preserve the original data so the math is traceable, and give analysts a workflow to review and approve before anything goes to an auditor.

Here's how I structured it.

---

## Schema overview

```
Company
  └─ IngestionBatch (one per file upload)
       └─ EmissionRecord (one per data row)
            └─ EmissionFactor (the conversion factor used)
```

---

## Company — multi-tenancy

Everything hangs off `Company`. Every queryset in every view filters by `company_id`. The idea is simple: two clients can never see each other's data because we never query without that filter.

This is app-level multi-tenancy, not database-level (like Postgres row-level security). For this prototype that's the right call — RLS requires more infrastructure setup than a 4-day sprint allows, and it would make local development significantly more complicated. If this went to production with 20+ clients on the same database, I'd add RLS on top of the app-level filtering as a belt-and-suspenders measure.

---

## EmissionFactor — why this is a table, not a constant

The original version had `2.68` hardcoded as the diesel conversion factor. That's a problem for two reasons.

First, auditability. If an auditor asks "where did that 2.68 come from and is it current?", you can't answer from a Python constant. With the `EmissionFactor` table, every record points to a row that says: "DEFRA 2024 Greenhouse Gas Reporting Conversion Factors, Table 3a, valid from April 1 2024, source URL included."

Second, factors change. DEFRA publishes updated factors every April. The Indian grid emission factor (which comes from the CEA CO2 Baseline Database, not DEFRA) is updated roughly annually. When a new version comes out, I add a new row with a later `valid_from` date. Old records are unaffected — they still point to the factor that was current when they were created.

The `EmissionRecord` also stores `emission_factor_used` as a decimal snapshot of the value at calculation time. This means even if the `EmissionFactor` table is modified or a row deleted, every historical record still knows exactly what number produced its CO2e figure.

Fields:
- `activity_type` — e.g. "Diesel", "Grid Electricity - India", "Flight - Economy Long-Haul"
- `unit_from` — the unit of the raw activity (L, kWh, km, nights, kg)
- `factor_value` — the conversion rate to kgCO2e
- `source_name` — full citation, e.g. "DEFRA 2024 GHG Conversion Factors — Table 3a"
- `source_url` — direct link to the published document
- `valid_from` — which reporting year this factor applies from
- `notes` — any caveats (e.g. "includes radiative forcing multiplier")

---

## IngestionBatch — import-level tracking

One row per file upload. This is separate from record-level data because import-level and row-level failures are different problems.

If a 200-row SAP export has 3 rows that fail to parse (bad date format, missing unit code), I want to know that at the batch level — not just see 197 records appear with no explanation for the missing 3. The `error_log` field is a JSONField that stores a list of `{row, error, data}` objects so an analyst can see exactly which rows failed and why, without reopening the original file.

Fields that matter:
- `original_filename` — chain of custody starts here. Auditors want to know which file produced which numbers.
- `total_rows` / `rows_ingested` / `rows_failed` / `rows_flagged` — the four numbers tell you at a glance whether an upload was clean
- `status` — COMPLETE, PARTIAL (some rows failed), or FAILED (entire file unreadable)
- `error_log` — JSONField list of parse failures with the original row data included

---

## EmissionRecord — the core table

One row per normalised emission activity. The design follows three rules:

**Rule 1: Never overwrite raw data.**
`raw_quantity` and `raw_unit` hold exactly what was in the source file. `normalized_quantity` and `normalized_unit` are after unit conversion only (e.g. m³ → L, gallons → L). `co2e_kg` is the final output. If someone disputes a number, I can show them the chain: source row → unit conversion → emission factor → final CO2e. That chain is broken the moment you start overwriting fields.

**Rule 2: Preserve the original row.**
`raw_row_data` is a JSONField that stores the entire CSV row as-is at the time of ingestion. This means if a source file gets lost or overwritten, every record still carries a copy of the exact line that produced it. This is not optional for audit purposes.

**Rule 3: Record who approved what and when.**
`reviewed_by`, `reviewed_at`, and `audit_notes` form the approval trail. The `reviewed_at` timestamp matters specifically because GHG Protocol verification requires that data was reviewed and locked before the reporting period ended — not retroactively signed off after submission.

**The flag system:**
`flag` can be NONE, SUSPICIOUS, or DUPLICATE. SUSPICIOUS is set automatically by the ingestion parser when a row's value is more than 2.5× the recent average for that category and company. This catches obvious data entry errors (e.g. 45,000 kWh when the norm is 4,500) before they reach the auditor. The analyst still makes the call — the flag just surfaces the record for attention.

---

## Scope assignment

Scope is set at ingestion based on source type and activity category:

- **Scope 1** — direct combustion of fuels the company controls. Diesel, petrol, CNG consumed in company vehicles and generators. Source: SAP.
- **Scope 2** — purchased electricity. The electricity grid generates emissions; the company purchases the output. Source: utility portal.
- **Scope 3** — value chain emissions outside direct control. Business travel is Category 6 under the GHG Protocol. Source: corporate travel platform.

This prototype handles Scope 1 fuel and Scope 2 electricity exactly as defined in the GHG Protocol Corporate Standard. It does not handle Scope 1 process emissions or fugitive emissions, Scope 2 heat or steam, or the other 14 Scope 3 categories — those are explicitly documented in TRADEOFFS.md.

---

## Unit normalisation flow

```
raw_quantity (raw_unit)
    → normalize to standard unit (L, kWh, km, nights, kg)
        → multiply by emission_factor_used
            → co2e_kg
```

The normalisation step handles unit variants that appear in real source data:
- SAP can report diesel volumes in L, M3 (cubic metres), or GAL. M3 is converted to L by × 1000. GAL by × 3.785.
- CNG is reported in KG and stays in KG — the emission factor is per kg.
- kWh and km need no conversion — they're already in the expected unit.