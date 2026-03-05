# =============================================================
# Market Intelligence Backend - Scraper Engine
# Multi-stage build for production deployment on Hostinger VPS
# =============================================================
FROM python:3.11-slim AS base

# System dependencies for Playwright Chromium
# Note: We install deps manually instead of playwright install-deps
# to avoid missing package issues on different Debian versions
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    fonts-noto-color-emoji \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libexpat1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxshmfence1 \
    xdg-utils \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only to save space)
# Skip install-deps since we manually installed dependencies above
RUN playwright install chromium

# Copy application code
COPY . .

# Create data directory for SQLite database persistence
RUN mkdir -p /app/data

# Setup cron job for automated scraping (runs every 6 hours)
RUN echo "0 */6 * * * cd /app && python scraper.py >> /var/log/scraper.log 2>&1" > /etc/cron.d/scraper-cron \
    && chmod 0644 /etc/cron.d/scraper-cron \
    && crontab /etc/cron.d/scraper-cron

# Create entrypoint script
RUN echo '#!/bin/bash\n\
    echo "[BOOT] Starting Market Intelligence Backend..."\n\
    echo "[BOOT] Running initial scrape..."\n\
    python scraper.py\n\
    echo "[BOOT] Initial scrape complete. Starting cron daemon..."\n\
    cron -f' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Health check
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "import sqlite3; conn = sqlite3.connect('/app/data/market_intel.db'); conn.close()" || exit 1

CMD ["/app/entrypoint.sh"]
