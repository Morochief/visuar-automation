import os
import json
import threading
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import create_engine, text
import math

# ============================================================
# VISUAR MARKET INTELLIGENCE - API SERVER
# Lightweight Flask API for on-demand scraping triggers
# ============================================================

app = Flask(__name__)
CORS(app)

logger = logging.getLogger("api_server")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | [%(name)s] | %(message)s'
)

JSON_OUTPUT_DIR = os.environ.get("JSON_OUTPUT_DIR", "/app/output")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/market_intel.db")

# TODO (Tech Debt): Implement Flask-Caching here (e.g., Cache(app, config={'CACHE_TYPE': 'simple'})) 
# and use @cache.cached(timeout=300) on /api/live_data when traffic increases to prevent DB spam.
engine = create_engine(DATABASE_URL)

# ── Scrape State ────────────────────────────────────────────
_scrape_state = {
    "running": False,
    "last_result": None,
    "error": None,
    "progress": None
}
_scrape_lock = threading.Lock()


def _run_scrape_thread():
    """Execute pipeline in a background thread."""
    import asyncio
    from scraper import MarketIntelligenceEngine

    global _scrape_state

    try:
        logger.info("[API] Background scrape started")
        engine_obj = MarketIntelligenceEngine()
        
        # Periodic progress update task in a separate thread/loop if possible, 
        # or just pass a callback to the engine. For now, let's use a shared ref or simple loop.
        def update_local_progress():
            while True:
                with _scrape_lock:
                    if not _scrape_state["running"]:
                        break
                    _scrape_state["progress"] = engine_obj.progress
                import time
                time.sleep(1)

        progress_thread = threading.Thread(target=update_local_progress, daemon=True)
        progress_thread.start()

        result = asyncio.run(engine_obj.run_pipeline())
        
        # Use lock for thread-safe state update
        with _scrape_lock:
            _scrape_state["last_result"] = result
            _scrape_state["error"] = None
            _scrape_state["progress"] = engine_obj.progress
        logger.info(f"[API] Background scrape completed: {result}")
    except Exception as e:
        logger.error(f"[API] Scrape failed: {e}", exc_info=True)
        with _scrape_lock:
            _scrape_state["error"] = str(e)
            _scrape_state["last_result"] = None
    finally:
        with _scrape_lock:
            _scrape_state["running"] = False


# ── Endpoints ───────────────────────────────────────────────

@app.route('/api/live_data', methods=['GET'])
def get_live_data():
    """Fetches real-time market margins with pagination."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        with engine.connect() as conn:
            # Query the view opportunity_margin_vw
            query = text('''
                SELECT 
                    product_id, name, brand, capacity_btu, internal_cost,
                    visuar_price, bristol_price, gg_price, gg_name, real_margin_percent,
                    diff_percent, status, last_updated
                FROM opportunity_margin_vw
                ORDER BY 
                    -- Sort by LOSS first, then margin
                    CASE WHEN status = 'LOSS' THEN 0 ELSE 1 END ASC,
                    ABS(diff_percent) DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            ''')
            
            result = conn.execute(query, {"limit": limit, "offset": offset})
            
            rows = []
            for r in result:
                rows.append({
                    "id": str(r.product_id),
                    "name": r.name,
                    "brand": r.brand,
                    "btu": r.capacity_btu,
                    "internal_cost": float(r.internal_cost) if r.internal_cost is not None else None,
                    "visuar_price": float(r.visuar_price) if r.visuar_price is not None else None,
                    "gg_price": float(r.gg_price) if r.gg_price is not None else None,
                    "gg_name": r.gg_name,
                    "lowest_comp": float(r.bristol_price) if r.bristol_price is not None else None,
                    "real_margin_percent": float(r.real_margin_percent) if r.real_margin_percent is not None else None,
                    "diff_percent": float(r.diff_percent) if r.diff_percent is not None else None,
                    "status": r.status,
                    "last_updated": r.last_updated.isoformat() if r.last_updated else None
                })
            
            # Get total count
            count_query = text('SELECT COUNT(*) FROM opportunity_margin_vw')
            total = conn.execute(count_query).scalar()
            
            # Additional KPI metrics from DB
            metrics_query = text('''
                SELECT 
                    SUM(CASE WHEN status = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    AVG(CASE WHEN status = 'LOSS' THEN diff_percent ELSE NULL END) as avg_diff
                FROM opportunity_margin_vw
            ''')
            metrics = conn.execute(metrics_query).fetchone()
            
            match_query = text('''
                SELECT count(DISTINCT product_id) 
                FROM competitor_products 
                WHERE competitor_id != (SELECT id FROM competitors WHERE name = 'Visuar')
                  AND product_id IS NOT NULL
            ''')
            exact_match = conn.execute(match_query).scalar() or 0
            
            ai_query = text("SELECT count(DISTINCT suggested_product_id) FROM pending_mappings WHERE match_score >= 80")
            ai_matched = conn.execute(ai_query).scalar() or 0
            
            total_products_query = text("SELECT count(*) FROM products")
            total_products = conn.execute(total_products_query).scalar() or 0
            
            stats = {
                "total": total_products,
                "page": page,
                "limit": limit,
                "total_pages": math.ceil(total / limit) if limit > 0 else 0,
                "wins": int(metrics.wins) if metrics and metrics.wins else 0,
                "losses": int(metrics.losses) if metrics and metrics.losses else 0,
                "avgDiff": float(metrics.avg_diff) if metrics and metrics.avg_diff else 0.0,
                "exact_match": exact_match,
                "partial_match": 0,
                "no_match": total_products - exact_match,
                "ai_matched": ai_matched
            }
            
            return jsonify({
                "rows": rows,
                "stats": stats
            }), 200

    except Exception as e:
        logger.error(f"[API] Error fetching live data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "visuar-scraper"})


@app.route('/api/scrape', methods=['POST'])
def trigger_scrape():
    """Trigger an on-demand scrape. Returns immediately, scrape runs in background."""
    with _scrape_lock:
        if _scrape_state["running"]:
            return jsonify({
                "status": "already_running",
                "message": "Un scraping ya esta en ejecucion. Espera a que termine."
            }), 409

        _scrape_state["running"] = True
        _scrape_state["error"] = None

    thread = threading.Thread(target=_run_scrape_thread, daemon=True)
    thread.start()

    return jsonify({
        "status": "started",
        "message": "Scraping iniciado. Usa /api/status para verificar el progreso."
    }), 202


@app.route('/api/status', methods=['GET'])
def scrape_status():
    """Check current scrape status and last results."""
    metadata = {}
    metadata_path = os.path.join(JSON_OUTPUT_DIR, "scrape_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception:
            pass

    with _scrape_lock:
        return jsonify({
            "scraping": _scrape_state["running"],
            "last_result": _scrape_state["last_result"],
            "error": _scrape_state["error"],
            "metadata": metadata
        })


if __name__ == '__main__':
    port = int(os.environ.get("API_PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
