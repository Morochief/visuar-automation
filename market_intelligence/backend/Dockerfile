# =============================================================
# Market Intelligence Backend
# Scraper + API Server for on-demand triggers
# =============================================================
FROM python:3.11-slim AS base

# System dependencies for Playwright Chromium
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

# Install Playwright browsers (Chromium only)
RUN playwright install chromium

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/data /app/output

# Setup cron job for automated scraping (every 6 hours)
RUN echo "0 */6 * * * cd /app && python pipeline.py >> /var/log/scraper.log 2>&1" > /etc/cron.d/scraper-cron \
    && chmod 0644 /etc/cron.d/scraper-cron \
    && crontab /etc/cron.d/scraper-cron \
    && touch /var/log/scraper.log

# Copy and setup entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && sed -i 's/\r$//' /app/entrypoint.sh


# Expose API port
EXPOSE 5000

# Health check via API
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5000/health || exit 1

CMD ["/app/entrypoint.sh"]
