# Visuar Automation: Stable Baseline Logic

This document serves as the "source of truth" for core logic that has been verified to work. Future modifications must consult this to avoid regressions in item counts or data quality.

## 1. Visuar Scraper
**Verified Count**: 73 Products
**Stable Loading Strategy**: 
- Use the direct "View All" parameter in the URL: `?resultsPerPage=9999999`. 
- **URL**: `https://www.visuar.com.py/hogar/aires-acondicionados/?resultsPerPage=9999999`
- **Why**: Standard pagination and "Next" buttons are brittle. This parameter ensures all products load in a single DOM state.

## 2. Gonzalez Gimenez (GG) Scraper
**Verified Count**: 68 Products
**Stable Loading Strategy**:
- **Popup Bypass**: The site uses an Insider popup. Verified selector for the close button is `.ins-close-button`. The `Escape` key also works.
- **Infinite Scroll**: Requires a dynamic loop that scrolls to the bottom and monitors the item count until it hits ~68 or finds the text `- Se llegó al final de la lista -`.
- **Brand Identification**: Brands are embedded in title strings (e.g., "Acondicionador de Aire TOKYO"). Logic must look for specific keywords (`TOKYO`, `SAMSUNG`, `GOODWEATHER`) rather than just taking the first word.

## 3. Data Integrity Rules
- **Price Extraction**: Always look for "Gs." and clean the numeric string.
- **Matching**: 24-25 items typically require AI Matching; the rest are matched via SKU automatically. Do not confuse "Items in Matching" with "Total Items Scraped".
