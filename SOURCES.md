# Data Sources and Real World Constraints

Here is my research on the three data sources, why I created the sample data this way, and what would probably break in a real production environment.

## SAP Data (Scope 1)
Real SAP exports are usually massive and have a lot of financial columns like cost centers and vendor IDs that we do not need for carbon math.

I made my sample data look like it was already cleaned up by a data pipeline. It only has Volume, Unit, Fuel Type, and Date. I did this because feeding 50 columns into an emissions calculator is just bad design.

In the real world, this would break because SAP dates are often formatted differently depending on the region. Also, companies use weird internal codes for fuel instead of just writing out "Diesel". We would need a mapping tool to fix that before uploading.

## Utility Data (Scope 2)
Most electricity data comes from PDFs or basic portal exports. They usually include meter numbers and pricing details along with the actual kilowatt hours.

I created the sample data to only include the kWh used and the billing date. I completely removed all the dollar amounts. Keeping financial data in the same table as carbon data is a bad idea for security and makes the system too complicated.

This would definitely break in real life because electricity bills rarely start exactly on the first of the month. They also send estimated bills and correct them later. The system would need a way to handle overlapping dates and those corrections.

## Corporate Travel (Scope 3)
Travel tools like Concur export huge files with employee names, passport details, and seat numbers.

I built my sample data to only have the distance, flight class, and date. I left out all the personal information on purpose. Storing employee names in a carbon database is a huge privacy risk.

The biggest breaking point here is multi leg flights. A flat CSV might say someone flew from New York to Singapore. But if they flew economy for one half and business for the other half, the flat CSV will calculate the footprint wrong because business class has a higher carbon cost. We would need actual airport routing codes to do it right.