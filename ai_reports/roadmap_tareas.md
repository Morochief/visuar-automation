# Visuar Market Intelligence - Task List

## Phase 1: Debugging Core Infrastructure [x]
- [x] Analyze `api_server.py` and `scraper.py` entrypoint.
- [x] Fix 502/503 errors by daemonizing the API server boot.
- [x] Verify data flow via internal health-check.

## Phase 2: Gonzalez Gimenez Scraper Fix [x]
- [x] Inspect GG DOM structure using browser subagent.
- [x] Implement robust CSS selectors for `.product` and `.product-title`.
- [x] Add automated scrolling and User-Agent spoofing to bypass lazy-loading/blocks.
- [x] Verify ingestion count (Successfully reached 24 records).

## Phase 3: AI Matcher Optimization [x]
- [x] Debug UUID format error (sanitizing `#` prefixes).
- [x] Implement **Auto-Apply** logic for matches > 85% confidence.
- [x] Verify semantic matching success for GG/Bristol products.

## Phase 4: Frontend Robustness [x]
- [x] Fix infinite loading loop in `PriceHistoryChart.tsx` for zero-match products.
- [x] Rebuild frontend container and verify UI layout.

## Phase 5: Final Validation [x]
- [x] Run full pipeline sync (Visuar -> Bristol -> GG).
- [x] Verify comparison charts are populated in the live dashboard.
- [x] Update `walkthrough.md` with victory screenshots.
- [x] Handover to USER.

## Phase 6: Stability & Progress Visibility [x]
- [x] Increase Nginx rate limits and burst for backend API.
- [x] Implement `progress` tracking in `MarketIntelligenceEngine`.
- [x] Expose `progress` in `api_server.py`.
- [x] Add defensive `Array.isArray` checks in React components.
- [x] Update UI to show real-time scrape progress.

## Phase 7: Performance & Extensibility [x]
- [x] Add unit tests for `ai_matcher.py` (pytest).
- [x] Implement Redis caching layer for API responses.
- [x] Add `/health` endpoint with DB/Redis checks.
- [x] Add `/metrics` endpoint for Prometheus monitoring.
- [x] Move brand list to database (admin panel ready).
- [x] Update documentation with new features.

## Phase 8: Bug Fixes & Dashboard Visibility [x]
- [x] Fixed "Last Scrape Time" not updating by syncing `scraper.py` with metadata updates.
- [x] Documented the discrepancy and fix in `problemas_soluciones.md`.
