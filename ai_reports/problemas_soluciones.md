# Registro de Problemas y Soluciones

## Problema: Fecha de último scrapeo no se actualiza en el Dashboard

**Fecha:** 2026-03-12
**Estado:** Resuelto

### Descripción
El dashboard principal mostraba una fecha de "Ultima actualización" que no cambiaba, incluso después de ejecutar una sincronización manual exitosa.

### Análisis Técnico
El proyecto cuenta con dos motores de scraping:
1. `pipeline.py`: Un script independiente que actualiza tanto la base de datos como el archivo `scrape_metadata.json`.
2. `scraper.py`: El motor integrado con el API (Flask) que se activa desde el botón "Sincronizar Datos".

Se descubrió que `scraper.py` actualizaba correctamente la base de datos PostgreSQL, pero **no actualizaba** el archivo `scrape_metadata.json`. Como el frontend (Astro/React) depende de este archivo JSON para mostrar el timestamp global del dashboard, la hora permanecía estática.

### Solución Implementada
Se modificó `market_intelligence/backend/scraper.py` para incluir el método `_update_metadata()`. Este método ahora se invoca al finalizar la fase de exportación JSON (`_save_json`), asegurando que `scrape_metadata.json` se actualice con la hora actual (UTC) y los contadores de productos extraídos.

### Verificación
- Se verificó la escritura del archivo en el volumen compartido.
- Al activar el botón de sincronización, el dashboard ahora refresca la hora automáticamente al finalizar el proceso.

## Problema: El Dashboard no muestra el progreso en tiempo real (aparece como "Scraping en progreso...")

**Fecha:** 2026-03-12
**Estado:** Resuelto

### Descripción
Incluso después de iniciar el scraping, el usuario no podía ver en qué etapa estaba el proceso (ej. "Scraping Visuar", "Matching AI"). Esto generaba la sensación de que el sistema estaba "colgado".

### Análisis Técnico
El sistema realiza el scrapeo en fases secuenciales: Visuar -> Bristol -> Gonzalez Gimenez (GG) -> Sincronización DB -> Matching con IA. 

Anteriormente:
1. El endpoint `/api/status` no devolvía el campo `progress`, por lo que el Dashboard mostraba un mensaje genérico.
2. Al llegar al 100% de la fase de GG (24/24), el scraper pasaba a la fase de **Sincronización** y **Matching con IA**. Como estas fases no enviaban actualizaciones de progreso, el Dashboard se quedaba "congelado" mostrando el último estado de la fase anterior (GG 24/24), aunque el proceso seguía corriendo en segundo plano.

### Solución Implementada
- **Backend API**: Se modificó `api_server.py` para exponer el campo `progress` en tiempo real.
- **Granularidad de Progreso**: Se inyectaron llamadas a un callback de progreso dentro de `ai_matcher.py` y en el ciclo de sincronización de base de datos en `scraper.py`.
- **Feedback Continuo**: Ahora el sistema informa explícitamente cuando entra en las fases de "Syncing Data" y "Matching AI", mostrando cuántos productos está procesando.

### Verificación
- El Dashboard ya no se queda estancado en "24/24 GG". 
- El Usuario recibe feedback visual durante todo el ciclo de vida del scraping, incluyendo el matching semántico con inteligencia artificial.

## Problema 3: Pérdida de Datos en Gonzalez Gimenez (GG)
### Descripción
Durante el monitoreo, el usuario notó que solo se scrapeaban 24 artículos de GG, cuando se esperaba un número mayor (~68). El indicador mostraba "24/24", dando la impresión de que el proceso había terminado con éxito pero con datos incompletos.

### Análisis Técnico
El sitio de Gonzalez Gimenez utiliza **scroll infinito** para cargar productos en lotes de 12. 
- La lógica anterior realizaba exactamente 4 scrolls fijos.
- 4 scrolls + carga inicial = 2 lotes visibles = 24 productos.
- Una vez finalizados los scrolls, el scraper contaba los productos encontrados y establecía ese número como el "total" de la fase (de ahí el "24/24").

### Solución Implementada
- **Scroll Dinámico**: Se reemplazó el bucle de scroll fijo por uno dinámico que monitorea el número de productos en el DOM.
- **Detección de Fin de Página**: El scraper sigue scrolleando y esperando a que cargue nuevo contenido hasta que el número de productos deja de aumentar (con reintentos para asegurar que no sea solo un lag de red).
- **Target Count**: Se ajustó el contador de progreso para reflejar el objetivo real de ~68 productos.

### Verificación
- Se compararon los resultados con una inspección manual del sitio (68 productos totales).
- Se confirmó en los logs que el scraper ahora supera el límite de 24 items.

## Problema 4: Error de sintaxis en el build del frontend (data.json.js)

**Fecha:** 2026-03-13
**Estado:** Resuelto

### Descripción
El proceso de levantado del proyecto (`docker compose build`) fallaba sistemáticamente en la etapa de construcción del frontend Astro. El error indicaba un fallo de análisis (parsing) en `src/pages/api/data.json.js` debido a una sintaxis de JavaScript inválida.

### Análisis Técnico
Al inspeccionar `market_intelligence/frontend_app/src/pages/api/data.json.js`, se identificó que la función `fetchDashboardData` tenía un bloque `catch` al final, pero le faltaba la palabra clave `try` al inicio de la función. Además, la función intentaba devolver un objeto `Response` de la API de Fetch, lo cual es incorrecto para una función interna que es llamada por un wrapper de caché; ésta debería devolver directamente el objeto de datos.

### Solución Implementada
- Se añadió el bloque `try { ... }` faltante al inicio de la función `fetchDashboardData`.
- Se modificó el retorno de la función para que devuelva el objeto `{ rows, stats }` en lugar de un `Response(JSON.stringify(...))`.
- Se ajustó el manejo de errores para que lance (throw) el error, permitiendo que el wrapper superior lo gestione correctamente.

### Verificación
- Se reinició el proceso de `docker compose build`.
- El proceso de construcción de Astro finalizó correctamente sin errores de sintaxis en el entrypoint del servidor.

## Problema 5: Error de iptables al crear red de Docker (DOCKER-ISOLATION-STAGE-2)

**Fecha:** 2026-03-13
**Estado:** Resuelto

### Descripción
Al ejecutar `docker compose up -d`, el sistema fallaba al intentar crear la red `market_intelligence_visuar_network`. El error indicaba que el comando `iptables` falló porque la cadena `DOCKER-ISOLATION-STAGE-2` no existe.

### Análisis Técnico
Se identificó un conflicto crítico de infraestructura: el sistema tenía **dos versiones de Docker** ejecutándose simultáneamente:
1.  **Versión Standard (/usr/bin/docker)**: Instalada vía repositorios APT.
2.  **Versión Snap (/snap/bin/docker)**: Instalada vía Snap.

Ambos daemons intentaban gestionar las mismas tablas de `iptables` en el kernel, lo que provocaba que las cadenas de Docker (como `DOCKER-FORWARD`, `DOCKER-ISOLATION-STAGE-1/2`) no se inicializaran correctamente o se corrompieran al reiniciar el servicio. El usuario estaba intentando usar la versión standard, pero el daemon de Snap estaba interfiriendo con la configuración de red global del kernel.

### Solución Implementada
1.  **Desactivación de Redundancia**: Se detuvo y desactivó el servicio de Docker en Snap (`sudo snap stop docker`) para eliminar el conflicto.
2.  **Limpieza de Reglas**: Se realizó un flush completo de las iptables (`iptables -F`, `iptables -X`) para permitir una reconstrucción limpia por parte del daemon principal.
3.  **Restauración de Servicio**: Se reinició el daemon standard y su socket (`systemctl restart docker.socket docker.service`).
4.  **Liberación de Puertos**: Se identificaron y eliminaron procesos `docker-proxy` zombies que mantenían ocupados puertos críticos (como el 6379 de Redis) tras la caída de los daemons previos.

### Verificación
- Se ejecutó `sudo iptables -S -t filter` confirmando que Docker volvió a crear todas sus cadenas de aislamiento.
- Se ejecutó `docker compose up -d` con éxito.
- Todos los servicios (`visuar_proxy`, `visuar_dashboard`, `visuar_postgres`, `visuar_cache`, `visuar_scraper`) están en estado **Up** y operativos.
## Problema 6: TypeError: NetworkError (Fallo de comunicación entre contenedores)

**Fecha:** 2026-03-13
**Estado:** Resuelto (Workaround aplicado)

### Descripción
Incluso con todos los contenedores en estado **Up**, el Dashboard mostraba un `NetworkError` al intentar consultar `/backend/api/live_data`. Los logs internos del backend mostraban `Connection timed out` al intentar conectar con PostgreSQL (`postgres:5432`) y Redis, a pesar de estar en la misma red de Docker.

### Análisis Técnico
Se identificó un fallo en el **Hairpin NAT / Routing** del bridge de Docker, posiblemente causado por un estado corrupto del kernel tras un corte de energía eléctrica. Aunque el host podía comunicarse con los contenedores, los contenedores no podían comunicarse entre sí directamente a través de sus IPs de bridge (`172...`), pero sí podían hacerlo a través del **Gateway del Host** (`172.50.0.1`).

### Solución Implementada
Se aplicó un **Workaround de Red Robusta**:
1.  **Exposición de Puertos**: Se expuso el puerto 5000 del backend al host para permitir el acceso vía gateway.
2.  **Mapeo de Host-Gateway**: Se modificó `docker-compose.yml` utilizando `extra_hosts` para forzar que los nombres de servicio (`postgres`, `redis`, `visuar_scraper`) apunten a `host-gateway`.
3.  **Bypass de Bridge**: Esto obliga a que el tráfico inter-servicio pase por la capa del Gateway (Host), la cual se verificó como funcional, evitando el routing directo fallido del bridge.

### Verificación
- Se ejecutó un test de socket desde `visuar_scraper` hacia `postgres` usando el alias resuelto por el gateway, resultando en éxito.
- El Dashboard ahora carga las métricas de PostgreSQL sin errores de red.
- La salud de los contenedores pasó a estado **healthy**.

## Problema 7: Error 502 Bad Gateway en nginx (Comunicación nginx → Frontend)

**Fecha:** 2026-03-13
**Estado:** Resuelto

### Descripción
Después de aplicar el workaround de host-gateway para el backend, el nginx seguía mostrando "An error occurred" (502 Bad Gateway) al intentar acceder a http://localhost:8080/. Los logs de nginx mostraban "upstream timed out" al intentar conectarse a `172.50.0.2:4321`.

### Análisis Técnico
Se identificó que:
1. El nginx utilizaba nombres de servicios Docker (`visuar_dashboard:4321`, `visuar_scraper:5000`) para los upstreams.
2. El DNS de Docker resolvía estos nombres a IPs del bridge (`172.50.0.x`), pero el routing entre contenedores estaba fallido (mismo problema del bridge corrupto).
3. El workaround de `extra_hosts` aplicado al servicio de nginx no funcionó correctamente porque las entradas en `/etc/hosts` apuntaban a la red wrong (`172.17.0.1` en lugar de `172.50.0.1`).

### Solución Implementada
Se modificó la configuración de nginx (`nginx/nginx.conf`) para que los upstreams apuntaran directamente al gateway de la red Docker personalizada (`172.50.0.1`), que es el host gateway funcional:

```nginx
upstream frontend {
    server 172.50.0.1:4321;
}

upstream backend_api {
    server 172.50.0.1:5000;
}
```

Además, se añadió la configuración de `extra_hosts` al servicio de nginx en `docker-compose.yml` para garantizar la resolución correcta de nombres de servicio.

### Verificación
- Se verificó conectividad desde el contenedor nginx hacia `172.50.0.1:4321` → **Éxito**
- Se verificó acceso a http://localhost:8080/ → **HTTP 200 OK**
- El Dashboard ahora carga correctamente en el navegador.

## Problema 8: Backend no puede acceder a internet (Scraping falla con Timeout)

**Fecha:** 2026-03-13
**Estado:** Resuelto

### Descripción
El scraper del backend mostraba "Timeout 60000ms exceeded" al intentar conectar a www.visuar.com.py. El backend estaba en una red Docker personalizada que no tenía acceso a internet.

### Análisis Técnico
Se identificó que:
1. El bridge de Docker personalizado (`172.50.0.0/16`) tenía problemas de routing hacia internet
2. El workaround de `extra_hosts` no resolví a conectividad externa
3. Los contenedores en la red personalizada no podían hacer NAT hacia internet

### Solución Implementada
Se cambió la arquitectura de red para usar `network_mode: host` en los servicios críticos:

1. **Backend** (`docker-compose.yml`):
   ```yaml
   network_mode: host
   ```

2. **Nginx** (`docker-compose.yml`):
   ```yaml
   network_mode: host
   ```

3. **nginx.conf**: Se actualizó para escuchar en puerto 8080 (en lugar de rely en mapeo de puertos de Docker):
   ```nginx
   server {
       listen 8080;
       ...
   }
   ```

### Verificación
- Backend puede conectarse a https://www.visuar.com.py/ → **Éxito**
- http://localhost:8080/ → **HTTP 200 OK**
- El scraping ahora funciona correctamente
