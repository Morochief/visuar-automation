import os
import json
import threading
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

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
    from pipeline import run_pipeline

    global _scrape_state

    try:
        logger.info("[API] Background scrape started")
        result = asyncio.run(run_pipeline())
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
