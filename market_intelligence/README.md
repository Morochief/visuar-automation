# Market Intelligence Engine

An end-to-end price tracking pipeline correlating multi-platform data into a canonical PostgreSQL dataset, visualized via a React/Astro Engine.

## Structure
- `/database`: Contains DDL queries (`init.sql`) including canonical master tables, historical trace-logs, alerting rules, and the calculation `opportunity_margin_vw` View logic.
- `/backend`: The robust Ingestion Engine. Includes:
  - **Scraper pipeline:** Built with Playwright (stealth mode) to scrape competitors.
  - **AI Matcher (`ai_matcher.py`):** Uses NVIDIA API (DeepSeek-v3.2) for semantic product correlation.
  - **Alert Engine (`alert_engine.py`):** Evaluates price/stock changes against user-defined rules with anti-spam cooldowns.
- `/frontend`: High-impact Astro/React visual components featuring KPIs and competitive tables tailored for Senior Market intelligence tracking.
- `docker-compose.yml`: Automated full-stack spin-up (Frontend, Backend, and Database).

## Run Book (Docker)
1. Build and boot the entire stack: 
   ```bash
   docker compose up --build -d
   ```
2. Access the Dashboard at: `http://localhost:8080` (or `https://localhost:4443`)
3. Access the API (internal) via: `http://localhost:8080/backend/`

## Manual Local Development
If you need to run the python scripts outside of Docker:
1. Seed Virtual env & Dependencies: `cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
2. Install Playwright binaries: `playwright install chromium`
3. Set your API Key for AI Matching: `export NVIDIA_API_KEY="your-key"`
4. Trigger the extraction & alerts: `python scraper.py`
