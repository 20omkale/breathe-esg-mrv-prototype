# Engineering Decisions and Resolved Ambiguities

During this short sprint, I had to make a few calls to keep the system stable and finish on time.

First, I had to figure out how to handle emission factors. Doing the exact math requires huge databases that change all the time. I decided to hardcode standard emission factors for this prototype, like using 2.68 for diesel and 0.4 for grid electricity. If I could ask the product manager, I would want to know if we are going to buy an external API for this later or build our own lookup tables.

Second, I had to decide what happens if someone uploads a corrected file for a month they already finished. I went with an append-only approach. The system takes the new file as a fresh batch, and the analyst can just reject the old records and approve the new ones. We never delete data so we don't lose the history.

For what to handle, I stuck to Scope 1 fuel volume from SAP, Scope 2 electricity from utilities, and Scope 3 business travel. I completely ignored things like fugitive emissions or purchased goods because that requires complex math and API integrations that just do not fit in a four day window.