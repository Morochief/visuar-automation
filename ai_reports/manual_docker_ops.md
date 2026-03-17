# Guía de Gestión de Contenedores Docker

Esta guía contiene los comandos esenciales para monitorear, depurar y administrar los contenedores del proyecto de Market Intelligence.

---

## 1. Monitoreo de Estado

### Ver estado resumido (formateado)
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```
*   **Explicación**: Muestra solo la información crítica de los contenedores que están **corriendo**.
    *   `{{.Names}}`: Nombre del contenedor (ej. `visuar_scraper`).
    *   `{{.Status}}`: Tiempo activo y salud (`healthy`/`unhealthy`).
    *   `{{.Ports}}`: Puertos mapeados hacia el exterior.

### Ver todos los contenedores (incluso los detenidos)
```bash
docker ps -a
```
*   **Explicación**: Útil para ver si un contenedor se detuvo por un error. Si ves un estado `Exited (1)`, significa que el proceso falló.

---

## 2. Logs y Diagnóstico

### Ver logs en tiempo real (Follow)
```bash
docker logs -f [nombre_contenedor]
```
*   **Explicación**: Abre el flujo de salida del contenedor. Verás lo que está pasando **en vivo**. Presiona `Ctrl + C` para salir.
*   **Ejemplo**: `docker logs -f visuar_scraper` para ver el progreso del scraping elemento por elemento.

### Ver las últimas N líneas
```bash
docker logs --tail 50 [nombre_contenedor]
```
*   **Explicación**: Muestra solo las últimas 50 líneas. Evita que la terminal se inunde con meses de historial.

---

## 3. Administración de Servicios

### Reiniciar un contenedor específico
```bash
docker restart [nombre_contenedor]
```
*   **Explicación**: Detiene y vuelve a arrancar el contenedor. Útil si el servicio parece "congelado" o para aplicar cambios leves.

### Reiniciar todo el proyecto (vía Docker Compose)
```bash
docker compose restart
```
*   **Explicación**: Reinicia los 4 servicios (db, scraper, dashboard, proxy) en el orden correcto de dependencias. *Nota: Debes ejecutarlo desde la carpeta `market_intelligence`.*

---

## 4. Comandos de Emergencia / Mantenimiento

### Forzar ejecución del scraper (Manual)
```bash
docker exec -it visuar_scraper python scraper.py
```
*   **Explicación**: Entra al contenedor vivo y ordena ejecutar el script de scraping inmediatamente, sin esperar al cron o al API.

### Acceder a la terminal interna del contenedor
```bash
docker exec -it [nombre_contenedor] /bin/sh
```
*   **Explicación**: Te permite "entrar" al contenedor para explorar archivos o verificar configuraciones internas.

### Ver consumo de recursos
```bash
docker stats
```
*   **Explicación**: Muestra en tiempo real cuánto CPU y RAM está consumiendo cada contenedor. Crucial para prevenir bloqueos en el VPS por falta de memoria.

---

## Tip de Oro: Alias de Terminal
Si quieres ahorrar tiempo, puedes agregar esto a tu archivo `.bashrc` o `.zshrc`:
```bash
alias dps='docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
```
¡Luego solo escribes `dps` y verás tu tabla personalizada!
