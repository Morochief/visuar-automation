# Visuar Market Intelligence - Technical Documentation

> **Versión:** 2.0  
> **Fecha:** 2026-03-10  
> **Estado:** Producción  

---

## 1. Resumen Ejecutivo

El **Visuar Market Intelligence** es un sistema de inteligencia de precios que monitorea automáticamente los precios de aires acondicionados en competidores del mercado paraguayo (Bristol, González Giménez) comparándolos con el catálogo de Visuar.

### Principales Mejoras (v2.0)

| Área | Mejora | Impacto |
|------|--------|---------|
| **Seguridad** | API Keys fuera del código | Previene fugas de credenciales |
| **Estabilidad** | Retry con Exponential Backoff | Resiliencia ante fallos de red |
| **Concurrencia** | Thread-safe state management | Previene race conditions |
| **AI** | DeepSeek con Thinking | Mejor precisión en matching |
| **Bug Fix** | KPIs funcionando | Dashboard muestra datos correctos |

---

## 2. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           INTERNET                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      NGINX (Reverse Proxy)                              │
│                   Puerto: 80 (HTTP) / 443 (HTTPS)                      │
│         Rate Limiting │ Gzip │ Security Headers │ Routing             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │   FRONTEND       │           │    BACKEND       │
        │   Astro/React    │           │   Python Flask    │
        │   Puerto: 4321   │           │   Puerto: 5000   │
        │   Puerto: 8080   │           │   Puerto: 5000   │
        └───────────────────┘           └───────────────────┘
                    │                               │
                    │       ┌───────────────┐       │
                    │       │  SHARED JSON  │       │
                    │       │    VOLUME     │       │
                    │       └───────────────┘       │
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
        ┌───────────────────────────────────────────┐
        │            POSTGRESQL DATABASE             │
        │            Puerto: 5432                    │
        │  products │ competitor_products │ price_logs│
        │  alert_rules │ notifications_log          │
        └───────────────────────────────────────────┘
```

### Componentes

| Servicio | Tecnología | Función |
|----------|------------|---------|
| **Nginx** | nginx:alpine | Reverse proxy, SSL, cache, rate limiting |
| **Frontend** | Astro 5 + React 19 | Dashboard visual con KPIs |
| **Backend** | Python 3.11 + Flask | API REST + Scraper + AI |
| **Database** | PostgreSQL 15 | Almacenamiento persistente |

---

## 3. Flujo de Datos

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  COMPETIDORES │     │   BACKEND    │     │   DATABASE   │
│              │     │              │     │              │
│ visuar.com   │────▶│  Playwright  │────▶│  SQLite/PG   │
│ bristol.com  │     │  (Scraper)   │     │  (Storage)   │
│ gg.com.py    │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  AI MATCHER  │
                     │ DeepSeek v3  │
                     │ + Thinking   │
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ ALERT ENGINE │
                     │ (Notificaciones)
                     └──────────────┘
```

### Proceso de Scraping

1. **Trigger**: Manual (API) o Automático (Cron cada 6 horas)
2. **Extracción**: Playwright con headless Chromium
3. **Normalización**: Extracción de BTU, marca, inverter desde nombres
4. **Almacenamiento**: Logs de precios en base de datos
5. **Matching**: AI (DeepSeek) o Fuzzy matching para mapear productos
6. **Alertas**: Evalúa reglas de precio y notifica

---

## 4. Stack Tecnológico

### Backend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Python** | 3.11 | Lenguaje principal |
| **Playwright** | 1.42.0 | Web scraping automatizado |
| **Flask** | 3.1.0 | API REST |
| **SQLAlchemy** | 2.0.29 | ORM |
| **OpenAI SDK** | 1.14+ | Integración NVIDIA DeepSeek |

### Frontend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Astro** | 5.17.1 | Framework SSR |
| **React** | 19.2.4 | Componentes interactivos |
| **TailwindCSS** | 4.2.0 | Estilos |
| **Lucide React** | 0.575.0 | Iconos |
| **XLSX** | 0.18.5 | Export a Excel |

### Base de Datos

| Tecnología | Uso |
|------------|-----|
| **PostgreSQL 15** | Producción |
| **SQLite** | Desarrollo local |
| **Views SQL** | Cálculos de margen |

### DevOps

| Tecnología | Uso |
|------------|-----|
| **Docker** | Contenedores |
| **Docker Compose** | Orquestación |
| **Nginx** | Reverse proxy |
| **Cron** | Tareas programadas |

---

## 5. Cambios Implementados (v2.0)

### 5.1 Seguridad: API Keys Externas

**Problema:** Las API keys estaban hardcodeadas en el código fuente.

**Solución:** Variables de entorno via archivo `.env`

```python
# ANTES (inseguro)
NVIDIA_API_KEY = "nvapi-xxx...xxx"  # ¡EXPUESTO!

# DESPUÉS (seguro)
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
if not NVIDIA_API_KEY:
    raise ValueError("NVIDIA_API_KEY es requerida")
```

**Archivo de configuración:**
```bash
# market_intelligence/.env
NVIDIA_API_KEY=nvapi-tu_api_key_aqui
ENCRYPTION_KEY=tu_clave_secreta_aqui
FLASK_ENV=production
```

### 5.2 Estabilidad: Retry con Exponential Backoff

**Problema:** El scraper fallaba silenciosamente ante errores de red temporales.

**Solución:** Función de reintento con backoff exponencial

```python
async def retry_with_backoff(func, max_retries=3, base_delay=2):
    """Ejecuta una función con reintento exponencial."""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # 2s, 4s, 8s
                logger.warning(f"Retry {attempt+1}/{max_retries}: {e}. Esperando {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Todos los intentos fallidos: {e}")
    raise last_exception
```

**Aplicado a:**
- Navegación a Visuar
- Navegación a Bristol  
- Navegación a González Giménez

### 5.3 Concurrencia: Thread Safety

**Problema:** Múltiples hilos podían modificar `_scrape_state` simultáneamente.

**Solución:** Uso consistente de `_scrape_lock`

```python
# ANTES (race condition)
def _run_scrape_thread():
    global _scrape_state
    _scrape_state["running"] = True  # ❌ No seguro
    _scrape_state["progress"] = engine_obj.progress  # ❌ Race

# DESPUÉS (thread-safe)
def _run_scrape_thread():
    global _scrape_state
    with _scrape_lock:  # ✅ Seguro
        _scrape_state["running"] = True
    # ...
    with _scrape_lock:
        _scrape_state["progress"] = engine_obj.progress
```

### 5.4 AI: DeepSeek con Thinking

**Problema:** Matching de productos basado solo en texto, sin razonamiento.

**Solución:** Streaming con pensamiento extendido

```python
completion = client.chat.completions.create(
    model="deepseek-ai/deepseek-v3.2",
    messages=[...],
    temperature=0.1,
    max_tokens=8192,
    extra_body={"chat_template_kwargs": {"thinking": True}},
    stream=True
)

# Procesa reasoning + contenido
for chunk in completion:
    reasoning = chunk.choices[0].delta.reasoning_content
    content = chunk.choices[0].delta.content
```

**Beneficios:**
- Razonamiento transparente del AI
- Mejor precisión en matching de productos
- Debugging del proceso de decisión

### 5.5 Bug Fix: Dashboard KPIs

**Problema:** Variable indefinida `curr` causaba error en cálculos.

```javascript
// ANTES (error)
const sumWins = rows.filter(r => r.status === 'WIN' && curr.diff_percent !== null)
//                                            ^^^^ undefined!

// DESPUÉS (correcto)
const sumWins = rows.filter(r => r.status === 'WIN' && null)
// r.diff_percent !==                                                     ^
```

---

## 6. API Endpoints

### Backend (Puerto 5000)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/live_data` | Datos de márgenes en tiempo real |
| GET | `/health` | Health check |
| POST | `/api/scrape` | Iniciar scraping |
| GET | `/api/status` | Estado del scraping |

### Frontend (Puerto 4321)

| Endpoint | Descripción |
|----------|-------------|
| `/` | Dashboard principal |
| `/api/data.json` | Datos para gráficos |
| `/api/visuar_ac_data.json` | Catálogo Visuar |
| `/api/gg_ac_data.json` | Catálogo GG |
| `/api/approve_mapping.json` | Aprobar mappings |
| `/api/pending_mappings.json` | Ver mappings pendientes |

---

## 7. Base de Datos

### Esquema Principal

```sql
-- Productos canónicos (catálogo Visuar)
CREATE TABLE products (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    brand VARCHAR(100),
    capacity_btu INTEGER,
    is_inverter BOOLEAN,
    internal_cost DECIMAL(15, 2)
);

-- Productos de competidores
CREATE TABLE competitor_products (
    id SERIAL PRIMARY KEY,
    competitor_id INTEGER,
    product_id UUID REFERENCES products(id),
    name VARCHAR(255),
    capacity_btu INTEGER,
    sku VARCHAR(100),
    url TEXT
);

-- Logs de precios (histórico)
CREATE TABLE price_logs (
    id SERIAL PRIMARY KEY,
    competitor_product_id INTEGER,
    price DECIMAL(15, 2),
    is_in_stock BOOLEAN,
    scraped_at TIMESTAMP
);

-- Reglas de alertas
CREATE TABLE alert_rules (
    id SERIAL PRIMARY KEY,
    product_id UUID,
    target_price DECIMAL(15, 2),
    contact_info BYTEA,  -- Encriptado
    cooldown_hours INTEGER,
    is_active BOOLEAN
);
```

### View: Oportunidades de Margen

```sql
CREATE VIEW opportunity_margin_vw AS
-- Calcula automáticamente:
-- - visuar_price vs gg_price
-- - diff_percent (margen)
-- - status (WIN/LOSS/EQUAL)
```

---

## 8. Despliegue

### Requisitos

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| RAM | 2 GB | 4-8 GB |
| CPU | 1 vCPU | 2 vCPU |
| Disk | 10 GB | 20 GB |

### Pasos de Instalación

```bash
# 1. Clonar repositorio
cd /opt
git clone https://github.com/Morochief/visuar-automation.git

# 2. Configurar variables
cd market_intelligence
cp .env.example .env
nano .env  # Editar API keys

# 3. Build y start
docker compose up -d --build

# 4. Verificar
docker compose ps
docker compose logs -f backend
```

### URLs de Acceso

| Servicio | URL |
|----------|-----|
| Dashboard | http://tu-ip:8080 |
| API Backend | http://tu-ip:8080/backend/ |
| Health | http://tu-ip:8080/health |

---

## 9. Monitoreo y Logs

### Ver Logs

```bash
# Todos los servicios
docker compose logs -f

# Solo backend
docker compose logs -f backend

# Solo frontend
docker compose logs -f frontend

# Solo base de datos
docker compose logs -f postgres
```

### Health Checks

| Servicio | Endpoint | Expected |
|----------|----------|----------|
| Backend | `/health` | `{"status": "ok"}` |
| Frontend | `http://localhost:4321` | 200 OK |
| PostgreSQL | `pg_isready` | true |

---

## 10. Troubleshooting

### Problemas Comunes

| Problema | Solución |
|----------|----------|
| No hay datos en dashboard | Ejecutar `docker compose exec backend python scraper.py` |
| API key no funciona | Verificar con `docker compose exec backend env \| grep NVIDIA` |
| Memory error | Aumentar RAM del contenedor en docker-compose.yml |
| Timeout en scraping | Aumentar timeout en scraper.py |

---

## 11. Mantenimiento

### Backup de Base de Datos

```bash
docker compose exec postgres pg_dump -U visuar_admin market_intel_db > backup.sql
```

### Actualizar Código

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

### Escalar Horizontalmente

El sistema está diseñado para ejecutarse en un solo servidor. Para escalar:
1. Externalizar PostgreSQL a Cloud SQL (AWS RDS, GCP Cloud SQL)
2. Usar Redis para cache y sesiones
3. Container orchestration con Kubernetes

---

## 12. Roadmap Futuro

- [ ] Integración con más competidores
- [ ] Dashboard en tiempo real con WebSockets
- [ ] ML para predicción de precios
- [ ] Notificaciones Telegram/Slack
- [ ] Tests de integración automatizados
- [ ] Métricas Prometheus/Grafana

---

## 13. Contacto y Soporte

**Desarrollador:** Morochief  
**Repositorio:** https://github.com/Morochief/visuar-automation

---

*Documento generado automáticamente el 2026-03-10*
