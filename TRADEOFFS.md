# Architectural Tradeoffs

Because I only had four days, I skipped a few things on purpose to make sure the main data pipeline actually worked and didn't crash.

I did not build a real login system or role based access control. Setting up proper authentication takes way too much time, and I wanted to focus on the core carbon data problem instead of standard web app setup. 

I also skipped background workers like Celery. In real life, a massive CSV will time out if you process it directly while the user waits. But for this demo, I kept the infrastructure simple and just disabled the upload button in the UI while it processes the file.

Lastly, I left out dynamic unit conversions, like changing miles to kilometers or gallons to liters automatically. Data validation pipelines get really messy really fast. I forced a strict template for the prototype to prove the core math works without getting stuck writing code for edge cases.