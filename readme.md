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

# After pulling schema changes (UUID PKs), reset DB once then load data:
poetry run python scripts/reset_schema.py
poetry run python scripts/seed_example.py   # optional: no network
poetry run python -m pipeline.run --airlines ek,ba,ai --limit 5
poetry run python -m pipeline.run --airlines ek,ba,ai --skip-existing   # backfill net-new configs only

# Backend API
cd backend && poetry run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

See [docs/architecture.md](./docs/architecture.md) for full details.

## Phase 2 Development

### Data Pipeline

1. Build a Python data pipeline that can continuously extract cabin class flight features for target airline
2. Build a lightweight LLM module using the existing codebase to search for the websites associated with target airline cabin class product features
3. Extract the website URLs and extract the required data following the output schema provided. Use the existing prompt template as reference for good practice structure.
4. The data pipeline can be triggered manually by running the scripts from the terminal
5. The flight features are extracted at the airline > cabin class level. Integrate the dataset extracted with the existing database schema.

### Backend API

1. Build a FastAPI to support the frontend UI/UX
2. Put a small focus on the efficiency of serving the right information to optimise the load performance of the frontend

### Frontend UI

1. Create an additional page for aircraft config details where there will be 2 main sections -> top section will show the aircraft level details and bottom section will show cabin class level details. The cabin class level details section will show both the hardward features and cabin class flight features, with cabin classes across the columns and features across the row. It will look like a comparison across multiple cabin classes.
2. Add the cabin class flight features to the existing aircraft config comparison page to the bottom of the existing hardward features
3. Add an additional page just to show compare airline -> cabin class level instead of the aircraft config level
