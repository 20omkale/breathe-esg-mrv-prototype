Architectural and Product Decisions
Ambiguities Resolved
The core ambiguity was the specific format of the client data. "SAP exports" and "Utility data" are incredibly broad categories. I chose to narrow the scope to ensure a robust, working prototype rather than a fragile system attempting to handle every edge case.

SAP Data: I assumed a flat-file CSV export originating from an SAP IDoc or ALV grid. I chose to handle Fuel and Procurement volume while explicitly ignoring internal SAP metadata like Plant Codes and Cost Centers.

Utility Data: I opted for the CSV export from a utility provider portal. Parsing PDFs requires OCR which introduces significant error rates unsuitable for a four-day prototype.

Travel Data: I assumed a clean export from a platform like Navan or Concur that already provides the transport mode and distance, resolving the ambiguity of calculating distances from raw IATA airport codes.

Questions for the Product Manager
If this were a real sprint planning session, I would ask the PM the following questions before writing any code:

Are we expecting clients to upload these files manually via the dashboard, or are we building SFTP/API integrations for automated ingestion?

For utility data, do we need to prorate emissions if a billing cycle spans across two different calendar months or reporting quarters?

What is our fallback strategy when a travel export only provides airport codes without the flight distance?