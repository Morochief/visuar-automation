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
    "error": None
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
        result = asyncio.run(engine_obj.run_pipeline())
        with _scrape_lock:
            _scrape_state["last_result"] = result
            _scrape_state["error"] = None
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
            
            stats = {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": math.ceil(total / limit) if limit > 0 else 0
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
