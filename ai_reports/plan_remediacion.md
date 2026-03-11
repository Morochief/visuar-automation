# Remediation Plan: Code Review Fixes 🛡️

Este plan aborda los hallazgos críticos y de alta prioridad de la auditoría de código para mejorar la seguridad, estabilidad y calidad del proyecto Visuar Market Intelligence.

## User Review Required

> [!IMPORTANT]
> **NVIDIA API Key**: Se eliminará el valor por defecto en el código. Es obligatorio configurar la variable de entorno `NVIDIA_API_KEY` en el archivo `.env` o en el entorno de despliegue para que el Matcher de IA funcione.

## Proposed Changes

### [Security] Backend Credentials

#### [MODIFY] [ai_matcher.py](file:///home/morochief/Documents/visuar-automation/market_intelligence/backend/ai_matcher.py)
- Eliminar el valor por defecto de `NVIDIA_API_KEY` para evitar filtraciones en el repositorio.
- Lanzar una advertencia clara si la llave no está configurada.

#### [MODIFY] [alert_engine.py](file:///home/morochief/Documents/visuar-automation/market_intelligence/backend/alert_engine.py)
- Cambiar la lógica de `ENCRYPTION_KEY`: si no se detecta la variable en un entorno no-dev, el sistema debe fallar o loguear un error crítico en lugar de usar `'dev_key'`.

---

### [Stability] Scraper & Dashboard Reliability

#### [MODIFY] [Dashboard.tsx](file:///home/morochief/Documents/visuar-automation/market_intelligence/frontend_app/src/components/Dashboard.tsx)
- Corregir el bug en el cálculo de KPIs donde se referencia la variable inexistente `curr`. Cambiar a `r.diff_percent`.

#### [MODIFY] [scraper.py](file:///home/morochief/Documents/visuar-automation/market_intelligence/backend/scraper.py)
- Implementar lógica de reintento con **Exponential Backoff** para las funciones de navegación (`page.goto`). Intentar 3 veces antes de marcar la fuente como fallida.

#### [MODIFY] [api_server.py](file:///home/morochief/Documents/visuar-automation/market_intelligence/backend/api_server.py)
- Envolver las actualizaciones de `_scrape_state` con un `threading.Lock()` para evitar condiciones de carrera (Race Conditions) entre el hilo de scraping y el de la API.

---

## Verification Plan

### Automated Tests
- Ejecutar `python -m pytest` en el backend para asegurar que el `ai_matcher` y `alert_engine` siguen funcionando (configurando llaves de prueba).
- Verificar que el scrapero maneja timeouts sin colapsar el pipeline completo.

### Manual Verification
- Cargar el dashboard y verificar que los KPIs (Wins/Losses) se calculan correctamente.
- Simular un fallo de red durante el scraping para observar el reintento automático.
