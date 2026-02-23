# Market Intelligence Engine

An end-to-end price tracking pipeline correlating multi-platform data into a canonical PostgreSQL dataset, visualized via a React/Astro Engine.

## Structure
- `/database`: Contains DDL queries (`init.sql`) including canonical master tables and historical trace-logs, plus the calculation `opportunity_margin_vw` View logic.
- `/backend`: The robust Ingestion Engine built with Playwright (stealth mode) mapping canonical models and bridging gaps with fuzzy searching natively routed via SQLAlchemy.
- `/frontend`: High-impact React visual components featuring KPIs and competitive tables tailored for Senior Market intelligence tracking.
- `docker-compose.yml`: Automated local spin-up for the Postgres instance.

## Run Book
1. Boot up the DB: `docker-compose up -d postgres`
2. Seed Virtual env & Dependencies: `cd backend && pip install -r requirements.txt`
3. Install Playwright binaries: `playwright install chromium`
4. Trigger the extraction: `python backend/scraper.py`
