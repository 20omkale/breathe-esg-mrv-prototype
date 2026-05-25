Data Sources and Real-World Handling
1. SAP Fuel and Procurement
Real-World Format: SAP systems typically export data via ALV grids to Excel/CSV or output flat files via IDocs.

What I Learned: These exports are notoriously bloated. They include German column headers in legacy configurations and internal organizational data (Company Code, Plant, Cost Center) that are irrelevant to carbon tracking.

Sample Data Rationale: My sample data includes Plant_Code and Cost_Center to mimic this bloat. The ingestion logic proves we can extract only the Volume and Fuel_Type while ignoring the noise.

Deployment Risks: In production, this would break if the client's SAP localization uses commas for decimal separators (European standard) instead of periods, which would crash the Python float conversion.

2. Utility Electricity Data
Real-World Format: Utility portal CSV downloads.

What I Learned: Meter readings are often provided in absolute totals with billing periods that fluctuate (e.g., 28 days one month, 33 days the next).

Sample Data Rationale: The sample data focuses on the kWh_Used and Bill_Date, attaching it to a specific meter number.

Deployment Risks: Real utility data often includes estimated readings that are later corrected. The current system would break or double-count if a client uploads a correction file without a robust upsert/deduplication mechanism.

3. Corporate Travel (Concur/Navan)
Real-World Format: Expense management API payloads or CSV reports.

What I Learned: The carbon impact of a flight changes drastically depending on the cabin class due to the physical space taken up on the aircraft.

Sample Data Rationale: The sample includes Trip_Type and Flight_Class. The ingestion logic demonstrates judgment by applying a much higher emission multiplier for Business class compared to Economy.

Deployment Risks: Real travel data is incredibly messy. It often omits distances entirely. A production system would break if it cannot automatically geolocate the distance between two raw airport codes.