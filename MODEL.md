# Data Model Architecture

## Multi-Tenancy
Multi-tenancy is handled at the database level using a centralized `Company` model. Every `DataSource` and `EmissionRecord` is bound to a specific company via a Foreign Key. This ensures strict data isolation between enterprise clients while allowing the application to scale horizontally.

## Unified Emission Record
Instead of creating separate tables for Fuel, Electricity, and Travel, I implemented a unified `EmissionRecord` model. Real-world ESG reporting requires aggregating total emissions across all scopes. A unified table allows the React dashboard to easily query, filter, and paginate all pending records for an analyst without writing complex SQL unions or hitting multiple API endpoints.

## Source of Truth Tracking
Auditability is the core requirement for this platform. The `DataSource` model tracks the exact origin of the data, including the user who uploaded it and a reference to the raw file or API payload. Every `EmissionRecord` links back to its parent `DataSource`. If an auditor questions a row of normalized data, the analyst can trace it directly back to the original SAP export or Utility PDF.

## Unit Normalization
The `EmissionRecord` explicitly separates `raw_quantity` and `raw_unit` from `normalized_quantity` and `normalized_unit`. This allows analysts to see exactly what came from the source system alongside the normalized output. This separation prevents data loss during the conversion process and builds immense trust with the auditing team.