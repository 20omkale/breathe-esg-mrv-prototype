# Database Model and Architecture

I set up the database in PostgreSQL focusing on keeping data safe and trackable.

The first table is Company. Everything links back to this so we keep different tenants totally separate. If this was going to production, we would use row level security so clients could never see each other's data.

Next is DataSource. This tracks exactly where the data came from, who uploaded it, and when. In ESG reporting, knowing the origin of a number is just as important as the number itself. If an uploaded file had errors, we can trace the bad math back to the exact upload batch.

The main table is EmissionRecord. It holds both the raw data from the client and our system's normalized output. I mapped the scope category based on the source type right when it gets uploaded. For unit normalization, I made sure to keep both the raw input and the normalized output. Overwriting raw data ruins the audit trail, so we keep everything. Finally, there is a status flag. Records stay pending until an analyst actually approves them, which stops bad automated data from ruining the final carbon footprint.