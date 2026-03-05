import asyncio
import json
import os
import re
import logging
from datetime import datetime
from playwright.async_api import async_playwright

# ============================================================
# VISUAR MARKET INTELLIGENCE - UNIFIED PIPELINE
# Scrapes → JSON (for frontend) + SQLite (for history)
# ============================================================

JSON_OUTPUT_DIR = os.environ.get("JSON_OUTPUT_DIR", "/app/output")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | [%(name)s] | %(message)s'
)
logger = logging.getLogger("pipeline")

# ── Brand & BTU Extraction ──────────────────────────────────

KNOWN_BRANDS = [
    'SAMSUNG', 'LG', 'MIDEA', 'JAM', 'WHIRLPOOL', 'CARRIER', 'TOKYO', 'MIDAS',
    'GOODWEATHER', 'TCL', 'SPEED', 'MUELLER', 'ELECTROLUX', 'ALTECH', 'HITACHI',
    'MABE', 'VCP', 'CONTINENTAL', 'AURORA', 'CONSUL', 'FAMA', 'HAUSTEC', 'OSTER'
]

def normalize_btu(title: str):
    """Extract BTU capacity from product title."""
    title_lower = title.lower()
    title_norm = re.sub(r'(\d)\.(\d{3})', r'\1\2', title_lower)

    match = re.search(r'(\d{1,5})\s*(k|btu)', title_norm)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if unit == 'k' or val <= 60:
            return val * 1000
        return val

    match_exact = re.search(r'\b(9000|12000|18000|22000|24000|27980|28000|30000|36000|48000|60000)\b', title_norm)
    if match_exact:
        return int(match_exact.group(1))

    return None


def extract_brand(title: str, brand_hint: str = None) -> str:
    """Extract brand from title or hint."""
    if brand_hint and brand_hint.strip().upper() not in ('UNKNOWN', ''):
        return brand_hint.strip().upper()
    title_upper = title.upper()
    for b in KNOWN_BRANDS:
        if b in title_upper:
            return b
    first_word = title.split()[0].upper() if title else "UNKNOWN"
    return first_word if len(first_word) > 2 else "UNKNOWN"


# ── Scrapers ────────────────────────────────────────────────

async def scrape_visuar() -> list:
    """Scrape Visuar AC products with pagination support."""
    logger.info("[VISUAR] Starting scrape...")
    products = []
    seen_titles = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(
                "https://www.visuar.com.py/hogar/aires-acondicionados/",
                wait_until='networkidle',
                timeout=30000
            )

            while True:
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(1000)

                items = await page.query_selector_all('article.js-product-miniature')
                for item in items:
                    title_el = await item.query_selector('.product-title')
                    brand_el = await item.query_selector('.product-brand')
                    price_el = await item.query_selector('.product-price')
                    regular_price_el = await item.query_selector('.regular-price')

                    title = await title_el.inner_text() if title_el else ""
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)

                    brand_hint = await brand_el.inner_text() if brand_el else ""
                    brand = extract_brand(title, brand_hint)

                    price = 0.0
                    if price_el:
                        content = await price_el.get_attribute('content')
                        if content:
                            try:
                                price = float(content)
                            except ValueError:
                                pass

                    regular_price = None
                    if regular_price_el:
                        reg_text = await regular_price_el.inner_text()
                        clean = reg_text.upper().replace('₲', '').replace('GS', '').replace('.', '').replace(',', '').strip()
                        try:
                            regular_price = float(clean)
                        except ValueError:
                            pass

                    if title and price > 0:
                        products.append({
                            "name": title,
                            "price": price,
                            "regular_price": regular_price,
                            "btu": normalize_btu(title),
                            "is_inverter": 'inverter' in title.lower(),
                            "brand": brand
                        })

                # Try pagination
                try:
                    load_more = await page.query_selector('.next.js-search-link, .infinite-scroll-button')
                    if load_more and await load_more.is_visible():
                        await load_more.click()
                        await page.wait_for_timeout(3000)
                    else:
                        break
                except Exception:
                    break

        except Exception as e:
            logger.error(f"[VISUAR] Scrape error: {e}", exc_info=True)
        finally:
            await browser.close()

    logger.info(f"[VISUAR] Extracted {len(products)} products")
    return products


async def scrape_gg() -> list:
    """Scrape Gonzalez Gimenez AC products with infinite scroll."""
    logger.info("[GG] Starting scrape...")
    products = []
    seen_titles = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(
                "https://www.gonzalezgimenez.com.py/categoria/127/acondicionadores-de-aire",
                wait_until='networkidle',
                timeout=30000
            )

            # Infinite scroll to load all products
            prev_count = 0
            retries = 0
            while retries < 4:
                await page.mouse.wheel(0, 4000)
                await page.wait_for_timeout(1500)
                items = await page.query_selector_all('.product')
                if len(items) == prev_count:
                    retries += 1
                else:
                    retries = 0
                    prev_count = len(items)

            items = await page.query_selector_all('.product')
            logger.info(f"[GG] Found {len(items)} DOM elements after scrolling")

            for item in items:
                title_el = await item.query_selector('.product-title')
                price_el = await item.query_selector('.btn-cart-contado .current-price')
                if not price_el:
                    price_el = await item.query_selector('.product-price .current-price')

                old_price_el = await item.query_selector('.old-price-contado')
                if not old_price_el:
                    old_price_el = await item.query_selector('.btn-cart-contado .old-price')

                title = (await title_el.inner_text()).strip() if title_el else ""
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                brand = extract_brand(title)

                price = 0.0
                if price_el:
                    price_text = await price_el.inner_text()
                    clean = re.sub(r'[^\d]', '', price_text)
                    try:
                        price = float(clean)
                    except ValueError:
                        pass

                regular_price = None
                if old_price_el:
                    old_text = await old_price_el.inner_text()
                    clean = re.sub(r'[^\d]', '', old_text)
                    try:
                        regular_price = float(clean)
                    except ValueError:
                        pass

                if title and price > 0:
                    products.append({
                        "name": title,
                        "price": price,
                        "regular_price": regular_price,
                        "btu": normalize_btu(title),
                        "is_inverter": 'inverter' in title.lower(),
                        "brand": brand
                    })

        except Exception as e:
            logger.error(f"[GG] Scrape error: {e}", exc_info=True)
        finally:
            await browser.close()

    logger.info(f"[GG] Extracted {len(products)} products")
    return products


# ── JSON Export ─────────────────────────────────────────────

def categorize_by_brand(products: list) -> dict:
    """Group products by brand for JSON export."""
    categorized = {}
    for p in products:
        brand = p.get('brand', 'UNKNOWN').upper()
        if brand not in categorized:
            categorized[brand] = []
        categorized[brand].append({
            "name": p["name"],
            "price": p["price"],
            "regular_price": p.get("regular_price"),
            "btu": p.get("btu"),
            "is_inverter": p.get("is_inverter", False)
        })
    return categorized


def save_json(data, filename: str):
    """Save data to JSON file in the shared output directory."""
    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(JSON_OUTPUT_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"[EXPORT] Saved {filepath} ({os.path.getsize(filepath)} bytes)")


# ── Main Pipeline ───────────────────────────────────────────

async def run_pipeline() -> dict:
    """Execute the full scraping pipeline.

    Returns dict with scrape results summary.
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("[PIPELINE] Starting Market Intelligence Pipeline")
    logger.info("=" * 60)

    # Phase 1: Scrape both sources
    visuar_products = await scrape_visuar()
    gg_products = await scrape_gg()

    # Phase 2: Save as categorized JSON for the frontend
    visuar_categorized = categorize_by_brand(visuar_products)
    gg_categorized = categorize_by_brand(gg_products)

    save_json(visuar_categorized, "visuar_ac_data.json")
    save_json(gg_categorized, "gg_ac_data.json")

    # Phase 3: Save metadata
    elapsed = (datetime.now() - start_time).total_seconds()
    metadata = {
        "last_scrape": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "visuar_count": len(visuar_products),
        "gg_count": len(gg_products),
        "visuar_brands": sorted(visuar_categorized.keys()),
        "gg_brands": sorted(gg_categorized.keys())
    }
    save_json(metadata, "scrape_metadata.json")

    logger.info("=" * 60)
    logger.info(f"[PIPELINE] Complete in {elapsed:.1f}s | Visuar: {len(visuar_products)} | GG: {len(gg_products)}")
    logger.info("=" * 60)

    return metadata


if __name__ == "__main__":
    asyncio.run(run_pipeline())
