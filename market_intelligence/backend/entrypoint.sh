#!/bin/bash
echo "============================================"
echo "[BOOT] Market Intelligence Backend v2"
echo "============================================"

echo "[BOOT] Starting API server on port 5000 in background..."
nohup python api_server.py > /app/api_server.log 2>&1 &

echo "[BOOT] Running initial pipeline scrape..."
python scraper.py
echo "[BOOT] Initial scrape complete."

echo "[BOOT] Starting cron daemon..."
cron

# Keep container alive
tail -f /dev/null
