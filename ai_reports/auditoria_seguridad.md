# Deep Dive Técnico: Visuar Market Intelligence Engine 🚀

Este documento proporciona un análisis exhaustivo del sistema para su transferencia de conocimiento o integración con otros sistemas de IA.

## 1. Visión General
El proyecto es una plataforma de **Inteligencia de Precios en Tiempo Real** diseñada para el mercado paraguayo. Automatiza la captura, el emparejamiento semántico (IA) y la visualización de márgenes competitivos entre **Visuar** y competidores clave como **Gonzalez Gimenez** y **Bristol**.

---

## 2. Stack Tecnológico (The Engine Room)

### Backend (Python 3.10+)
- **Framework**: Flask (API ligera para triggers y consultas de estado).
- **Orquestación de Scraping**: Playwright (Async) para navegación headless, manejo de SPAs y evasión de bloqueos básicos.
- **ORM & DB**: SQLAlchemy con PostgreSQL 15.
- **Matching Engine**: OpenAI SDK integrado con **NVIDIA NIM (DeepSeek-v3.2)** para procesamiento de lenguaje natural.

### Frontend (Modern Web & Single Source of Truth)
- **Framework**: Astro + React.
- **Data Flow (DB-Driven)**: El frontend carece de lógica de procesamiento de datos o "guessing" (reglas de coincidencia locales). Consume directa y exclusivamente los KPIs agregados (`total`, `exact_matches`, `avg_diff`) que provienen de la Base de Datos a través del endpoint Python (`/backend/api/live_data`).
- **UI & Styling**: Tailwind CSS + Lucide Icons.
- **Visualización**: Componentes React personalizados para gráficos de barras comparativos y gestión de estados de carga, con dependencias reactivas a los cambios de la base PostgreSQL.

### Infraestructura (DevOps)
- **Containerización**: Docker & Docker Compose.
- **Proxy Inverso**: Nginx (Manejo de CORS, compresión Gzip y Rate Limiting).
- **Procesos en Segundo Plano**: Multi-threading mediante `threading` de Python y `nohup` para daemonización.

---

## 3. Arquitectura de Datos (The Lifeblood)

### Esquema de Base de Datos (PostgreSQL)
1. **`products`**: El catálogo maestro (canonical) de Visuar.
2. **`competitors`**: Entidades competidoras (GG, Bristol).
3. **`competitor_products`**: Productos capturados de la web. Contienen `raw_brand`, `sku` y `url`.
4. **`price_logs`**: Serie temporal de precios asociados a cada `competitor_product`.
5. **`pending_mappings`**: Sugerencias de IA para revisión humana.
6. **`scrape_logs`**: Auditoría de cada ejecución (tiempo, cantidad de éxitos, errores).

### Vistas Críticas
- **`opportunity_margin_vw`**: Una vista materializada (conceptual) que realiza el JOIN entre precios de Visuar y el último precio de competidores emparejados. Calcula:
  - `diff_percent`: (Precio_Comp - Precio_Visuar) / Precio_Visuar.
  - `status`: 'WIN' (Visuar más barato) o 'LOSS' (Competidor más barato).

---

## 4. Flujo de Trabajo del Backend (The Pipeline)

1. **Triggering**: Una petición `POST /backend/api/scrape` inicia un hilo en segundo plano.
2. **Scraping**:
   - Playwright navega a las categorías de climatización.
   - Implementa **Scroll Tiered** (desplazamiento por etapas) para disparar el Lazy Loading de imágenes y datos.
   - Extrae metadatos técnicos (BTU, Tecnología Inverter).
3. **Normalization**:
   - `_normalize_btu()`: Convierte strings como "12k" o "12.000 BTU" en enteros estandarizados (12000).
   - `_is_inverter()`: Identifica la tecnología mediante Regex sobre el título.
4. **AI Matching (DeepSeek)**:
   - Se agrupan los candidatos de Visuar más probables por BTU y marca.
   - Se envía un prompt estructurado a DeepSeek pidiendo un análisis de confianza.
   - **Auto-Apply**: Si la confianza es >85%, el sistema vincula automáticamente el `competitor_product` con el `product_id` maestro.
5. **Alert Engine**: Evalúa reglas de negocio y dispara notificaciones si un margen cae por debajo del umbral de rentabilidad.

---

## 5. Protecciones y Resiliencia
- **Nginx Rate Limiting**: Protege el backend de ataques de denegación de servicio (DoS) o spam de peticiones del frontend.
- **Defensive Frontend**: El Dashboard utiliza verificaciones de tipo (`Array.isArray`) para prevenir crashes si la API devuelve errores 50x.
- **Background Startup**: El servidor de la API arranca independientemente del scraping para garantizar que el Dashboard siempre responda (Health Check).

---
**Resumen para IA**: Este es un sistema de extracción ETL reactivo que utiliza LLMs para resolver el problema de la falta de SKUs comunes en la web, traduciendo nombres de productos ambiguos en relaciones de base de datos precisas para la toma de decisiones comerciales.
