# Deployment Guide - Visuar Market Intelligence on Hostinger VPS

## Architecture

```
Internet → Nginx (80/443) → Astro Frontend (4321)
                                    ↑
                              Shared JSON Volume
                                    ↑
                           Python Scraper (cron)
```

## Prerequisites

1. **Hostinger VPS** with Ubuntu 22.04+ (minimum 2GB RAM recommended)
2. **SSH access** to your VPS
3. **Domain** pointed to your VPS IP (optional, for SSL)

---

## Step 1: Prepare your VPS

SSH into your Hostinger VPS and install Docker:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Add your user to docker group (logout/login after)
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker compose version
```

## Step 2: Clone the Repository

```bash
cd /opt
sudo git clone https://github.com/Morochief/visuar-automation.git
cd visuar-automation/market_intelligence
```

## Step 3: Configure Environment

```bash
# Edit the .env file if needed
nano .env
```

If using the Alert Engine and AI Matcher, specify these in `.env`:
```env
# AI Product Matching (DeepSeek via NVIDIA)
NVIDIA_API_KEY=your_nvidia_api_key_here

# Alert Engine Notifications (Optional)
# SMTP_USER=alerts@yourdomain.com
# SMTP_PASS=your_smtp_password
# TELEGRAM_BOT_TOKEN=your_bot_token

# Security (PostgreSQL pgcrypto)
ENCRYPTION_KEY=your_secret_32_char_key_here
```
## Step 4: Build & Launch

```bash
# Build all images (first time takes ~5-10 min)
docker compose build

# Start everything in background
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## Step 5: SSL Setup (Recommended)

### Option A: Certbot (Free Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot -y

# Stop nginx temporarily
docker compose stop nginx

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy certs to project
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./nginx/ssl/

# Uncomment SSL lines in nginx/nginx.conf
# Then restart
docker compose up -d nginx
```

### Option B: Hostinger SSL

Download the SSL certificate from your Hostinger panel and place the files in `./nginx/ssl/`.

---

## Useful Commands

```bash
# View all container status
docker compose ps

# View scraper logs
docker compose logs -f backend

# View frontend logs
docker compose logs -f frontend

# Restart everything
docker compose restart

# Rebuild after code changes
docker compose build --no-cache
docker compose up -d

# Stop everything
docker compose down

# Stop and remove volumes (WARNING: deletes data)
docker compose down -v

# Force a manual scrape
docker compose exec backend python scraper.py

# Check database (PostgreSQL)
docker compose exec postgres psql -U visuar_admin -d market_intel_db -c "SELECT COUNT(*) FROM competitor_products;"

# Run migration (if updating an existing database)
docker compose exec -T postgres psql -U visuar_admin -d market_intel_db -v enc_key='SU_CLAVE_AQUI' < database/migrations/migrate_pgcrypto.sql
```

## Resource Requirements

| Service  | RAM    | CPU   | Disk  |
|----------|--------|-------|-------|
| Backend  | ~1.5GB | 1 CPU | 500MB |
| Frontend | ~256MB | 0.5   | 200MB |
| Nginx    | ~64MB  | 0.25  | 10MB  |
| **Total**| **~2GB** | **1.75** | **~1GB** |

> Recommended VPS: **Hostinger KVM 2** (2 vCPU, 8GB RAM) or **KVM 1** (1 vCPU, 4GB RAM)

## Troubleshooting

### Container won't start
```bash
docker compose logs backend  # Check for errors
docker compose build --no-cache backend  # Rebuild
```

### Playwright crashes
The scraper needs significant RAM for headless Chromium. Ensure your VPS has at least 2GB RAM.

### Frontend shows no data
The scraper must complete at least one run first. Force it:
```bash
docker compose exec backend python scraper.py
```

### Port 80 already in use
```bash
sudo lsof -i :80  # Find what's using port 80
# Or change the port in docker-compose.yml
```
