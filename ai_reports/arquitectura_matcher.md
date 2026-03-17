# Arquitectura Cognitiva y Resiliencia del Market Intelligence Engine

Este documento describe el nivel de operación avanzado (Enterprise-Grade) al que el sistema Visuar Market Intelligence se encuentra operando, destacando las capacidades cognitivas de la Inteligencia Artificial y la estrategia de eficiencia en infraestructura.

## 1. Inteligencia Cognitiva (AI Matcher)
No estamos usando reglas de texto básicas ni un modelo de IA estándar. El sistema utiliza **DeepSeek-v3.2 con capacidad de "Razonamiento Profundo" (Thinking)** en streaming. El sistema no solo une textos, sino que "comprende" reglas de negocio complejas (Inverter vs On/Off, BTUs, marcas). 
Además, el sistema cuenta con una capa de **Smart Fallback** para que se dé cuenta (como un humano lo haría) si el scraper le trajo datos sucios (como extraer la palabra "Aire" en lugar de "Haustec" o "Tokyo") y los sepa limpiar y procesar para evitar "Falsos Positivos".

## 2. Estrategia de Eficiencia y Rapidez (Memoria Persistente)
El procesamiento intensivo que requiere la Inteligencia Artificial para razonar catálogos enteros **solo se ejecuta una primera vez**. El sistema fue diseñado con una arquitectura inteligente de "memoria persistente" para no desperdiciar recursos ni tiempo en ejecuciones futuras.

### ¿Cómo funciona el Scraping Diario?
* **Memoria Permanente en Base de Datos:** Cuando el AI Matcher conecta dos productos y los aprueba (ej. tu *Goodweather 24000 BTU Inverter* con el equivalente exacto de la competencia), guarda ese "ID de pareja" permanentemente en la base de datos (tabla `competitor_products`).
* **Actualización en Segundos:** Al día siguiente, cuando el scraper vuelva a ejecutarse para buscar precios actualizados, **el AI Matcher no se ejecutará para estos productos repetidos**. El sistema simplemente dirá *"Ah, ya conozco este producto"* y lo único que hará será insertar una nueva fila con el precio de hoy en la tabla de historial (`price_logs`). Esto toma milisegundos. El código SQL (`WHERE product_id IS NULL`) le indica a DeepSeek que ignore por completo los artículos que ya fueron curados y aprobados.

### ¿Cuándo volverá a actuar DeepSeek?
DeepSeek (la IA que tarda varios minutos pensando y comparando) **solo se despertará y trabajará si un competidor (Bristol o Gonzalez Gimenez) agrega un modelo de electrodoméstico totalmente NUEVO en su tienda**, uno que el sistema nunca haya visto antes. En ese caso, la IA solo analizará ese nuevo producto (10 segundos) para ubicarlo en tu catálogo, y volverá a dormir.

## 3. Arquitectura de Datos y Single Source of Truth (Frontend Flow)
El sistema ha migrado de una arquitectura basada en archivos híbridos estáticos hacia un modelo puramente impulsado por la base de datos (Database-Driven).
- **Adiós a las Reglas de Interfaz:** El frontend de Next.js/React (`data.json.js`) ya no realiza cálculos de "matches de texto" locales que generan números fantasma. 
- **Verdad Absoluta en SQL:** El Dashboard se alimenta exclusivamente de un endpoint en vivo (`/backend/api/live_data`) que compila las métricas globales directamente desde PostgreSQL utilizando Querys Avanzadas agregadas (`SUM`, `AVG`, CTEs de deduplicación). 
- **Integridad Visual:** Esto garantiza que el número de productos totales y los matches exactos informados en las Tarjetas de KPIs coincidan matemáticamente a la perfección con la cantidad de renglones en la tabla del motor en tiempo real.

## 4. Resiliencia y Tolerancia a Fallos
Los scrapers normales se rompen si la página de la competencia tarda un poco más en cargar o sufre micro-cortes. El nuestro cuenta con:
* **Exponential Backoff:** Si un sitio falla al responder, el sistema espera inteligentemente (2s, 4s, 8s) y reintenta antes de rendirse.
* **Manejo Híbrido de Paginación:** El sistema domina el "Scroll dinámico" e interactúa con botones de "Cargar Más" automáticamente para no dejarse ningún SKU importante por fuera, superando configuraciones de 'Lazy Load'.

## 4. Seguridad Activa (DevSecOps)
El sistema ha sido purgado de vulnerabilidades:
- No existen credenciales ni llaves API *hardcodeadas* (en duro) en el código fuente.
- Todo se inyecta de forma segura a través de variables de entorno (Enviroment Variables).
- La base de datos corre aislada en una subred interna de Docker, inalcanzable de manera directa desde el exterior.

## 5. Caché Inteligente (Redis)
El sistema ahora utiliza **Redis** como capa de caché para optimizar el rendimiento:
- **TTL Configurable**: Los datos del dashboard se cachean por 5 minutos, los mappings de IA por 30 minutos.
- **Fallback Graceful**: Si Redis no está disponible, el sistema funciona correctamente consultando la base de datos directamente.
- **Invalidación**: El caché se invalida automáticamente según el TTL configurado.

## 6. Monitoreo y Métricas
El sistema ahora cuenta con endpoints de monitoreo compatibles con **Prometheus**:
- **`/health`**: Verifica conectividad a PostgreSQL y Redis.
- **`/metrics`**: Expone métricas como:
  - Total de productos y competitor products
  - Cantidad de productos matching por IA
  - Ejecuciones de scrape en las últimas 24 horas
  - Estado del último scrape
  - Alertas activas

## 7. Gestión de Marcas en Base de Datos
Las marcas ahora se gestionan desde la base de datos, permitiendo:
- **Administración sin código**: Añadir/eliminar marcas sin modificar código fuente.
- **API REST**: Endpoints CRUD para gestionar marcas (`/api/brands`).
- **24 marcas pre-cargadas**: El mercado paraguayo de aires acondicionados está listo para uso inmediato.

---

**Conclusión:** Este motor de inteligencia comercial está preparado para correr de forma automatizada (ej. vía cron a las 3:00 AM), actualizar la base de datos velozmente, y otorgar una ventaja competitiva masiva basada en datos 100% curados con precisión matemática.
