Engineering Tradeoffs
To deliver a sharp, highly functional data normalization model within four days, I deliberately chose not to build the following three features:

1. Asynchronous File Processing
Currently, the CSV ingestion happens synchronously in the Django view. If an enterprise client uploads a massive SAP export with hundreds of thousands of rows, the HTTP request will time out. In a real production environment, I would hand this processing off to a background task queue using Celery and Redis, notifying the frontend via WebSockets when the ingestion is complete.

2. Dynamic Emission Factor API Integration
The conversion factors (e.g., converting liters of diesel or kWh of electricity to kgCO2e) are hardcoded into the ingestion logic. Real ESG reporting requires pulling these factors from localized, constantly updated databases like the EPA or DEFRA. I traded this dynamic lookup for hardcoded values to keep the prototype self-contained and focused on the data model.

3. Comprehensive Role-Based Access Control (RBAC)
While the database schema includes a multi-tenant Company model and tracks the user who uploaded the data, the frontend dashboard currently bypasses strict authentication. Building secure JWT authentication and managing analyst vs. client permissions would have consumed time better spent on perfecting the data normalization logic.