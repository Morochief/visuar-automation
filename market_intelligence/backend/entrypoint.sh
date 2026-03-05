#!/bin/bash
echo "============================================"
echo "[BOOT] Market Intelligence Backend v2"
echo "============================================"

echo "[BOOT] Running initial pipeline scrape..."
python pipeline.py
echo "[BOOT] Initial scrape complete."

echo "[BOOT] Starting cron daemon..."
cron

echo "[BOOT] Starting API server on port 5000..."
exec python api_server.py
