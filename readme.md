# Flight Benchmarking

## [1] Aircraft Hardware Features

**Objective**: Extract the aircraft and cabin features for different aircraft configurations for target airlines

1. Data source: https://www.aerolopa.com/
2. Loop through the webpage for each aircraft configuration for a list of target airlines.
3. Extract the html for each aircraft configuration i.e. https://www.aerolopa.com/ek-359g
4. Process the html for each aircraft configuration using LLM (Langchain, gemini-2.5-pro) with an option to swap different LLM model to extract data based on the [output](./output.py) data structure provided. Use the example provided in the prompt for reference. Ensure that the prompt is optimised for the data extraction.
5. Create a set of schema that will properly store the data in a postgres database. I got a local postgres server and database prepared for this - emirates.benchmarking.\* we can use.
6. Load the extracted data into the created schema
7. Update the architecture docs

## [2] Cabin Class Flight Features

**Objective**: Extract the flight features for each cabin class for target airlines

1. Extract the airline websites for the target airlines that contain information about the cabin class features such as check-in priority, baggage alowance, boarding priority, amenity kits, or anoy other features
2. Extract the html for these pages
3. Process the html for each aircraft configuration using LLM (Langchain, gemini-2.5-pro) with an option to swap different LLM model to extract data based on the [output](./output.py) data structure provided. Use the example provided in the prompt for reference. Ensure that the prompt is optimised for the data extraction.
4. Create a set of schema that will properly store the data in a postgres database. I got a local postgres server and database prepared for this - emirates.benchmarking.\* we can use.
5. Load the extracted data into the created schema
6. Update the architecture docs

## Phase 1 Development

### Data Pipeline

1. Build a Python data pipeline that can continuously extract new and update existing aircraft configurations extracted from target source
2. The data pipeline can be triggered manually by running the scripts from the terminal

### Backend API

1. Build a FastAPI to support the frontend UI/UX
2. Put a small focus on the efficiency of serving the right information to optimise the load performance of the frontend

### Frontend UI

1. Build a React.js, Next.js and Tailwind CSS modern frontend UI and UX to display comparison of the aircraft configurations for various airlines in a tabular format
2. Start with 3 views.
   1. First view is the summary view of the stats for the fleet for each airline in a dashboard / tabular format
   2. Second view is the detail view of each aircraft configuration for all airlines in a compact tabular format / dashboard
   3. Third view is the comparison view for selected aircraft configurations, where columns could be the aircraft configurations selected and the rows would be all the features compared at the aircraft level and cabin level (based on selection of specific cabin class)
3. Ensure a standardised design system is used across the web app
4. Use https://www.eleken.co/ and https://www.lcmhub.com/ for inspiration on design system. Prefer compact and light theme.

### Codebase Organisation

1. Lets use a monolithic structure for our codebase
2. Organise it in a way that it is ready to deploy - React app on vercel and FastAPI backend on Railway

## Quick start (Phase 1)

```bash
cp .env.example .env   # set Neon DATABASE_URL, optional GOOGLE_API_KEY

poetry install

# After pulling schema changes, reset DB once then load data:
poetry run python scripts/reset_schema.py
poetry run python scripts/seed_example.py   # optional: no network
poetry run python -m pipeline.run --airlines ek,ba,ai --limit 5
poetry run python -m pipeline.run --airlines ek,ba,ai --skip-existing   # backfill net-new configs only

# Phase 2: cabin flight features (LLM web research → DB)
poetry run python scripts/seed_flight_example.py   # optional: EK example from output.py, no network
poetry run python -m pipeline.run_flight --airlines ek,ba,ai
poetry run python -m pipeline.run_flight --airlines ek --force   # re-run LLM research

# Phase 3: Emirates onboard F&B menu (API → clean/flatten → optional blank-title LLM → DB → enrich)
poetry run python -m pipeline.run_menu --date 2026-08-01 --flight 7 --origin DXB --destination LHR
poetry run python -m pipeline.run_menu --date 2026-08-01 --flight 7 --origin DXB --destination LHR --cabins business,economy
poetry run python -m pipeline.run_menu --date 2026-08-01 --flight 7 --origin DXB --destination LHR --force

# Batch many flights from a JSON config (see pipeline/menu_batch.example.json)
# Each extractions[] entry: date, flight, origin, destination; optional cabins / force / skip_existing
# Optional top-level defaults merge into every entry (per-entry keys win). CLI --force / --skip-existing override all.
poetry run python -m pipeline.run_menu_batch --config pipeline/menu_batch.example.json
poetry run python -m pipeline.run_menu_batch --config my_batch.json --skip-existing
poetry run python -m pipeline.run_menu_batch --config my_batch.json --dry-run

# Backend API
poetry run uvicorn backend.app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

New UI routes: `/aircraft/{svg_id}` (detail), `/compare/airlines` (airline-level flight benefits).

See [docs/architecture.md](./docs/architecture.md) for full details.  
See [docs/deployment.md](./docs/deployment.md) for Vercel + Railway deployment.

## Phase 2 Development

### Data Pipeline

1. Build a Python data pipeline that can continuously research cabin class flight features for target airlines
2. Use Gemini with Google Search grounding to find credible sources and extract structured cabin benefits
3. Return data following the `output.py` flight features schema. Use the EPD prompt template (`flight_features_research_prompt.py`) as reference.
4. The data pipeline can be triggered manually by running the scripts from the terminal
5. The flight features are extracted at the airline > cabin class level. Integrate the dataset extracted with the existing database schema.

### Backend API

1. Build a FastAPI to support the frontend UI/UX
2. Put a small focus on the efficiency of serving the right information to optimise the load performance of the frontend

### Frontend UI

1. Create an additional page for aircraft config details where there will be 2 main sections -> top section will show the aircraft level details and bottom section will show cabin class level details. The cabin class level details section will show both the hardward features and cabin class flight features, with cabin classes across the columns and features across the row. It will look like a comparison across multiple cabin classes.
2. Add the cabin class flight features to the existing aircraft config comparison page to the bottom of the existing hardward features
3. Add an additional page just to show compare airline -> cabin class level instead of the aircraft config level
