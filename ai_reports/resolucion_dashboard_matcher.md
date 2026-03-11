# Registro de Problemas y Soluciones: Dashboard y AI Matcher

A continuación se documentan todos los contratiempos técnicos experimentados, especialmente aquellos relacionados con la visualización de datos en el Dashboard y la sincronización de la Inteligencia Artificial, junto con las soluciones aplicadas para resolverlos.

---

### 1. El Dashboard mostraba "Cargando..." infinito o "Sin datos" (Desconexión de fuente de datos)
*   **Problema:** La interfaz frontend (componente principal) intentaba cruzar información dependiendo en parte de archivos estáticos `.json` que estaban oxidados o no se regeneraban a la velocidad de la IA. Aunque la IA estaba escribiendo en la base de datos, el archivo `data.json.js` (la API interna del frontend) no estaba sincronizada en tiempo real.
*   **Solución Aplicada:** Se reescribió por completo la lógica del endpoint interno `src/pages/api/data.json.js` para que **se conecte directamente a la base de datos PostgreSQL**. Ahora, ejecuta sentencias SQL (usando la librería `pg`) uniendo la tabla `products` con `competitor_products` en **tiempo real**. Las comparaciones ahora fluyen directamente de lo que la IA insertó hace milisegundos.

### 2. Congelamiento del Sistema por Conexiones Fantasmas (Zombies / Idle in transaction)
*   **Problema:** En cierto momento, la API dejó de responder por completo y el dashboard no mostraba ningún dato incluso tras las correcciones. Tras analizar la base de datos, detectamos que el proceso `ai_matcher.py` (o procesos de testing manual) habían fallado, dejando transacciones de base de datos abiertas (`idle in transaction`). Estas transacciones bloqueaban la tabla, creando un *deadlock*.
*   **Solución Aplicada:** Entramos directamente al motor PostgreSQL (`visuar_postgres`) e identificamos los procesos colgados en `pg_stat_activity`. Se ejecutó el comando de emergencia `SELECT pg_terminate_backend(pid)` para matar esas sesiones zombis. Inmediatamente después, se reinició la API de scraping, liberando el flujo de información.

### 3. Lentitud Extrema y "Agujero Negro" de Información
*   **Problema:** Estábamos frente a un proceso desesperantemente lento. La IA procesaba la lista entera de productos con el "Modo de Pensamiento Profundo" (Thinking Mode) encendido por cada ítem. Peor aún, el script en Python estaba configurado para **guardar (commit) solo tras haber procesado grupos de 10 productos**. El resultado: parecía que no pasaba nada durante horas.
*   **Solución Aplicada:**
    1.  **Aceleración**: Apagamos temporalmente el "Thinking Mode" para limpiezas masivas y pasamos el modelo a un modo "Inferencia Rápida" bajando el `max_tokens` y quitando streaming. 
    2.  **Commit Constante**: Modificamos el loop en `ai_matcher.py` para que haga `session.commit()` **cada 2 productos**. Así obligamos al sistema a inyectar resultados de forma intermitente y veloz, dando retroalimentación constante al usuario en el Dashboard.

### 4. Rechazos de Vinculación por Discrepancias en Literales de Marca (Capitalización)
*   **Problema:** La inteligencia artificial hacía su trabajo excelente deduciendo que un texto que decía "GW" o "Goodweather 18k" pertenecía a Goodweather, pero le asignaba puntajes altos (95%+) que luego **el sistema de guardado rechazaba** aplicando su lógica estricta. ¿El motivo? En la base la marca de Visuar figuraba como algo distinto o la capitalización no cruzaba lógicamente en `raw_brand` de los competidores.
*   **Solución Aplicada:** Realizamos una intervención vía base de datos usando consultas SQL (`UPDATE ... ILIKE`) para forzar una estandarización de las cadenas en la tabla `competitor_products` (e.g. todo "Samsung", "LG", "Goodweather" estricto). Se corrigió la lógica en Python para hacer comparaciones tolerantes a minúsculas (`brand_match = competitor_brand.lower().strip() == visuar_brand.lower().strip()`).

### 5. Inyección Forzada de Matches Huérfanos
*   **Problema:** Las demoras generaron una acumulación temporal enorme en la tabla lateral `pending_mappings` (donde la IA empuja sugerencias de alta certeza) pero no se materializaban como definitivos en la relación `competitor_products.product_id`.
*   **Solución Aplicada:** Una vez saneada la estructura, se ejecutó un Query puente (`UPDATE competitor_products cp SET product_id = ...`) obligando la migración oficial e inmediata de todas las evaluaciones superiores al 80% de confianza estancadas.

### 6. Métricas Duplicadas en el Dashboard (KPIs inflados a 146 Productos Totales)
*   **Problema:** Tras solucionar la vinculación correcta de los 17 "Matches Exactos", el usuario notó que el total de productos en los KPIs marcaba 146 en lugar del tamaño real del catálogo oficial (73). Descubrimos que durante pruebas anteriores, un script auxiliar había desvinculado por error el catálogo de Visuar. Como resultado, en la siguiente ejecución el motor de scraping no encontró los productos originales y creó 73 duplicados exactos en la tabla `products`, partiendo la base de datos en dos mitades (productos viejos con los matches vs productos nuevos con el catálogo de Visuar).
*   **Solución Aplicada:** 
    1. Se inyectó una consulta SQL avanzada (CTE) directo en PostgreSQL para fusionar y trasladar los vínculos de los competidores (`competitor_products`) desde los IDs viejos hacia los nuevos IDs clonados por el scraper.
    2. Se trasladaron las sugerencias pendientes de la IA (`pending_mappings`) a los nuevos IDs unificados.
    3. Se eliminaron los 73 productos originales que quedaron "huérfanos".
    4. El Dashboard ahora recuperó la integridad de su fuente de verdad (Single Source of Truth), mostrando exactamente 73 productos totales y las métricas cruzadas a la perfección.

---
**Estado Actual Post-Fix:**
El sistema procesa y renderiza asincrónicamente el mercado en tiempo real. 
El "Deep Thinking" ha sido restaurado y ahora logra operar establemente, ya que la base de datos se comunica fluidamente validando los resultados cada par de segundos sin bloqueos transaccionales.
