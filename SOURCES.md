# Data Sources and Real-World Constraints

Here is what I found when looking into the three data sources and where things would probably break in a real deployment.

For SAP and Scope 1, I learned that ERP exports are usually really messy and rely on internal company codes. The sample data I used is a clean, post-processed version with just volume, unit, fuel type, and date. In the real world, this would break because actual SAP files have dozens of useless financial columns and weird date formats. We would need a proper mapping screen before ingestion.

For Utility data and Scope 2, electricity is usually tracked in kilowatt hours on basic portal exports or PDFs. The sample data just has the usage and bill date. The real world problem here is that billing cycles almost never line up with exact calendar months, and utilities send estimated bills that they correct months later. The system would need extra logic to handle those true-ups.

For corporate travel and Scope 3, the carbon impact changes a lot depending on flight class. A business class seat takes up more space and has a bigger footprint than economy. My sample data includes trip type, distance, class, and date. In reality, this gets complicated with multi-leg flights where someone flies economy for one leg and business for another. Flat CSV exports usually fail to capture that routing accurately.