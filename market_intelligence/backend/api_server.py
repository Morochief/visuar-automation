import os
import json
import threading
import logging
from flask import Flask, jsonify, request, Response
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
    """Health check endpoint with database connectivity."""
    health_status = {
        "status": "ok",
        "service": "visuar-scraper",
        "checks": {}
    }
    
    # Check database connectivity
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["database"] = f"error: {str(e)}"
    
    # Check Redis connectivity (optional)
    try:
        redis_url = os.environ.get('REDIS_URL')
        if redis_url:
            import redis
            r = redis.from_url(redis_url)
            r.ping()
            health_status["checks"]["redis"] = "ok"
    except Exception as e:
        health_status["checks"]["redis"] = f"unavailable: {str(e)}"
    
    # Check if scrape is running
    with _scrape_lock:
        health_status["scrape_running"] = _scrape_state["running"]
    
    status_code = 200 if health_status["status"] == "ok" else 503
    return jsonify(health_status), status_code


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus-compatible metrics endpoint."""
    from datetime import datetime, timezone
    
    metrics_lines = []
    
    # Helper to add metric
    def add_metric(name, value, labels=None):
        label_str = "" if not labels else "{" + ",".join(f'{k}="{v}"' for k, v in labels.items()) + "}"
        metrics_lines.append(f"visuar_{name}{label_str} {value}")
    
    try:
        with engine.connect() as conn:
            # Count products
            total_products = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
            add_metric("products_total", total_products)
            
            # Count competitor products
            total_competitor = conn.execute(text("SELECT COUNT(*) FROM competitor_products")).scalar()
            add_metric("competitor_products_total", total_competitor)
            
            # Count AI matches
            ai_matched = conn.execute(text(
                "SELECT COUNT(*) FROM pending_mappings WHERE match_score >= 60"
            )).scalar()
            add_metric("ai_matched_total", ai_matched)
            
            # Count scrape logs
            recent_scrape = conn.execute(text(
                "SELECT COUNT(*) FROM scrape_logs WHERE started_at > NOW() - INTERVAL '24 hours'"
            )).scalar()
            add_metric("scrape_runs_24h", recent_scrape)
            
            # Latest scrape status
            last_scrape = conn.execute(text(
                "SELECT status, products_scraped, finished_at FROM scrape_logs "
                "WHERE finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1"
            )).fetchone()
            
            if last_scrape:
                add_metric("last_scrape_status", 1 if last_scrape.status == 'success' else 0, 
                          {"status": last_scrape.status or "unknown"})
                add_metric("last_scrape_products", last_scrape.products_scraped or 0)
            
            # Count alerts
            active_alerts = conn.execute(text(
                "SELECT COUNT(*) FROM alert_rules WHERE is_active = true"
            )).scalar()
            add_metric("active_alerts", active_alerts)
            
    except Exception as e:
        logger.error(f"[METRICS] Error collecting metrics: {e}")
        add_metric("errors_total", 1, {"type": "metrics_collection"})
    
    # Scrape state metrics
    with _scrape_lock:
        add_metric("scrape_running", 1 if _scrape_state["running"] else 0)
    
    # Timestamp
    metrics_lines.append(f"visuar_metrics_timestamp {int(datetime.now(timezone.utc).timestamp())}")
    
    return Response("\n".join(metrics_lines), mimetype='text/plain')


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
            "progress": _scrape_state["progress"],
            "metadata": metadata
        })


# ── Brands Management API ───────────────────────────────────────

@app.route('/api/brands', methods=['GET'])
def get_brands():
    """Get all active brands from database."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name, display_name, is_active, is_known "
                "FROM brands WHERE is_active = true ORDER BY name"
            ))
            brands = [dict(row._mapping) for row in result]
            return jsonify({"brands": brands}), 200
    except Exception as e:
        logger.error(f"[BRANDS] Error fetching brands: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/brands', methods=['POST'])
def add_brand():
    """Add a new brand to the database."""
    try:
        data = request.get_json()
        name = data.get('name', '').upper().strip()
        display_name = data.get('display_name', name)
        
        if not name:
            return jsonify({"error": "Brand name is required"}), 400
        
        with engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO brands (name, display_name) VALUES (:name, :display_name) "
                "ON CONFLICT (name) DO UPDATE SET display_name = :display_name"
            ), {"name": name, "display_name": display_name})
            conn.commit()
        
        return jsonify({"status": "success", "brand": name}), 201
    except Exception as e:
        logger.error(f"[BRANDS] Error adding brand: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/brands/<brand_name>', methods=['DELETE'])
def delete_brand(brand_name):
    """Deactivate a brand (soft delete)."""
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE brands SET is_active = false WHERE name = :name"
            ), {"name": brand_name.upper()})
            conn.commit()
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"[BRANDS] Error deleting brand: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("API_PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
