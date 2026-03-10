import asyncio
import json
import os
import logging
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict

from ai_matcher import run_ai_matching

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from playwright.async_api import async_playwright

from models import Base, Product, Competitor, PriceLog, CompetitorProduct, PendingMapping, ScrapeLog
from alert_engine import evaluate_alerts

import os
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/market_intel.db")
JSON_OUTPUT_DIR = os.environ.get("JSON_OUTPUT_DIR", "/app/output")

# SOC Enterprise Logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | MAR-INTEL | [%(name)s] | %(message)s'
)
logger = logging.getLogger("ingestion_engine")

class MarketIntelligenceEngine:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def _normalize_btu(self, title: str) -> Optional[int]:
        title_lower = title.lower()
        match = re.search(r'(\d{1,5})\s*(k|btu)', title_lower)
        if match:
            val, unit = int(match.group(1)), match.group(2)
            if unit == 'k' or val <= 60:
                return val * 1000
            return val
        match_exact = re.search(r'\b(9000|12000|18000|24000|30000|36000|60000)\b', title_lower)
        if match_exact: return int(match_exact.group(1))
        return None

    def _is_inverter(self, title: str) -> bool:
        return 'inverter' in title.lower()

    async def _scraped_results_visuar(self, page) -> list:
        # Visuar uses .js-product-miniature for products
        items = await page.query_selector_all('.js-product-miniature')
        results = []
        for item in items:
            # Try multiple link selectors for Visuar
            t_el = await item.query_selector('.product-title a') or await item.query_selector('a.product-thumbnail')
            p_el = await item.query_selector('.product-price')
            
            if not t_el: continue
            
            # Extract title properly
            title_el = await item.query_selector('.product-title')
            title = (await title_el.inner_text()).strip() if title_el else ""
            url = await t_el.get_attribute('href')
            
            # If relative URL, prepend domain
            if url and url.startswith('/'):
                url = "https://www.visuar.com.py" + url
            
            price = 0.0
            
            if p_el:
                content = await p_el.get_attribute('content')
                if content:
                    try: price = float(content)
                    except ValueError: pass
                else:
                    text = await p_el.inner_text()
                    clean = "".join(filter(str.isdigit, text))
                    try: price = float(clean)
                    except ValueError: pass
            
            # Basic brand/ref from listing if possible
            ref_el = await item.query_selector('.product-reference')
            brand_el = await item.query_selector('.product-brand')
            
            sku = await ref_el.inner_text() if ref_el else None
            brand = await brand_el.inner_text() if brand_el else None
            
            if title and price > 0:
                results.append({
                    "name": title.strip(), 
                    "price": price,
                    "url": url,
                    "sku": sku.strip() if sku else None,
                    "brand": brand.strip() if brand else None
                })
        return results

    async def _scraped_results_bristol(self, page) -> list:
        items = await page.query_selector_all('#catalogoProductos .it')
        results = []
        for item in items:
            t_el = await item.query_selector('.info .tit h2')
            p_el = await item.query_selector('.precios .venta .monto')
            
            title = await t_el.inner_text() if t_el else ""
            url = await t_el.get_attribute('href') if t_el else None
            price = 0.0
            if p_el:
                text = await p_el.inner_text()
                clean = text.upper().replace('GS', '').replace('.', '').replace(',', '').strip()
                try: price = float(clean)
                except ValueError: pass
            if title and price > 0:
                results.append({"name": title.strip(), "price": price, "url": url})
        return results

    async def _scraped_results_gg(self, page) -> list:
        # Gonzalez Gimenez uses .product or .item-catalogo
        items = await page.query_selector_all('.product.item-catalogo')
        if not items:
            items = await page.query_selector_all('.product')
            
        results = []
        for item in items:
            # Title is inside .product-title
            title_el = await item.query_selector('.product-title a')
            if not title_el:
                title_el = await item.query_selector('h3 a')
            
            title = await title_el.inner_text() if title_el else None
            url = await title_el.get_attribute('href') if title_el else None
            
            # Price extraction (Contado is the cash price we want)
            # It usually looks like "Gs. 5.989.000" inside the .btn-cart-contado section
            p_el = await item.query_selector('.btn-cart-contado span')
            if not p_el:
                p_el = await item.query_selector('.product-price span')
            
            price = 0.0
            if p_el:
                text = await p_el.inner_text()
                # If text is "18 x Gs. 615.000", we want the part after Gs.
                if "Gs." in text:
                    text = text.split("Gs.")[-1]
                clean = "".join(filter(str.isdigit, text))
                try: price = float(clean)
                except ValueError: pass
            
            if title and price > 0:
                # Brand is usually the first word
                brand = title.split()[0] if title else None
                results.append({
                    "name": title.strip(), 
                    "price": price,
                    "url": url,
                    "sku": None, # SKU is only in quickview/detail, skipping for speed
                    "brand": brand
                })
        return results

    def _save_json(self, visuar_data, bristol_data, gg_data):
        """Phase 2: Save as categorized JSON for legacy frontend features."""
        os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
        
        def categorize(products):
            cat = {}
            for p in products:
                brand = p.get('brand') or "UNKNOWN"
                if brand not in cat: cat[brand] = []
                cat[brand].append(p)
            return cat

        files = {
            "visuar_ac_data.json": categorize(visuar_data),
            "gg_ac_data.json": categorize(gg_data),
            "bristol_ac_data.json": categorize(bristol_data)
        }
        
        for name, data in files.items():
            path = os.path.join(JSON_OUTPUT_DIR, name)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[EXPORT] Saved {path}")

    async def run_pipeline(self):
        logger.info("[PIPELINE_START] Commencing Market Intelligence Data Ingestion")
        session = self.Session()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
            page = await context.new_page()
            
            # ── Visuar ──
            visuar_data = []
            visuar_log = ScrapeLog(started_at=datetime.now(timezone.utc), status='failed')
            try:
                comp_v = session.query(Competitor).filter_by(name='Visuar').first()
                if comp_v:
                    visuar_log.competitor_id = comp_v.id
                logger.info("Connecting to Visuar...")
                await page.goto("https://www.visuar.com.py/hogar/aires-acondicionados/", wait_until="networkidle")
                visuar_data = await self._scraped_results_visuar(page)
                visuar_log.status = 'success'
                visuar_log.products_scraped = len(visuar_data)
                logger.info(f"[SOURCE_A] Ingested {len(visuar_data)} records from Visuar")
            except Exception as e:
                visuar_log.error_message = str(e)
                logger.error(f"[SOURCE_A] Visuar scrape failed: {e}")
            finally:
                visuar_log.finished_at = datetime.now(timezone.utc)
                session.add(visuar_log)
            
            # ── Bristol ──
            bristol_data = []
            bristol_log = ScrapeLog(started_at=datetime.now(timezone.utc), status='failed')
            try:
                comp_b = session.query(Competitor).filter_by(name='Bristol').first()
                if comp_b:
                    bristol_log.competitor_id = comp_b.id
                logger.info("Connecting to Bristol...")
                await page.goto("https://www.bristol.com.py/climatizacion/climatizacion/splits", wait_until="networkidle")
                try:
                    await page.wait_for_selector('#catalogoProductos .it', timeout=10000)
                    await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.warning(f"Timeout waiting for elements on Bristol: {e}")
                bristol_data = await self._scraped_results_bristol(page)
                bristol_log.status = 'success'
                bristol_log.products_scraped = len(bristol_data)
                logger.info(f"[SOURCE_B] Ingested {len(bristol_data)} records from Bristol")
            except Exception as e:
                bristol_log.error_message = str(e)
                logger.error(f"[SOURCE_B] Bristol scrape failed: {e}")
            finally:
                bristol_log.finished_at = datetime.now(timezone.utc)
                session.add(bristol_log)

            # ── Gonzalez Gimenez ──
            gg_data = []
            gg_log = ScrapeLog(started_at=datetime.now(timezone.utc), status='failed')
            try:
                comp_g = session.query(Competitor).filter_by(name='Gonzalez Gimenez').first()
                if comp_g:
                    gg_log.competitor_id = comp_g.id
                logger.info("Connecting to Gonzalez Gimenez...")
                # Set a more realistic User-Agent
                await context.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                })
                await page.goto("https://www.gonzalezgimenez.com.py/categoria/127/acondicionadores-de-aire", wait_until="domcontentloaded")
                try:
                    await page.wait_for_selector('.item-catalogo', timeout=60000)
                    # Scroll tiered to bypass lazy loading
                    for i in range(1, 5):
                        await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {i/4})")
                        await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.warning(f"Timeout waiting for elements on GG: {e}")
                    await page.screenshot(path='/app/output/gg_debug.png')
                gg_data = await self._scraped_results_gg(page)
                gg_log.status = 'success'
                gg_log.products_scraped = len(gg_data)
                logger.info(f"[SOURCE_C] Ingested {len(gg_data)} records from Gonzalez Gimenez")
            except Exception as e:
                gg_log.error_message = str(e)
                logger.error(f"[SOURCE_C] GG scrape failed: {e}")
            finally:
                gg_log.finished_at = datetime.now(timezone.utc)
                session.add(gg_log)

            await browser.close()
            
            # ── Deep Scraping for unmatched ──
            # We do this before sync or after? 
            # Better after sync to know what is new/unmatched?
            # Actually, we can do it during sync or right after.
            
            # ── Database Sync ──
            self._sync_to_database(visuar_data, bristol_data, gg_data)
            
            # ── Targeted Deep Scraping (for those missing description/product_id) ──
            await self._run_targeted_deep_scrape()

            # ── Legacy JSON Export ──
            self._save_json(visuar_data, bristol_data, gg_data)

        # Commit scrape logs
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"[SCRAPE_LOGS] Failed to save scrape logs: {e}")
        finally:
            session.close()

    def _sync_to_database(self, visuar_data: List[Dict], bristol_data: List[Dict], gg_data: List[Dict] = None):
        session = self.Session()
        try:
            comp_visuar = session.query(Competitor).filter_by(name='Visuar').first()
            if not comp_visuar:
                comp_visuar = Competitor(name='Visuar', url='https://www.visuar.com.py/')
                session.add(comp_visuar)

            comp_bristol = session.query(Competitor).filter_by(name='Bristol').first()
            if not comp_bristol:
                comp_bristol = Competitor(name='Bristol', url='https://www.bristol.com.py/')
                session.add(comp_bristol)

            comp_gg = session.query(Competitor).filter_by(name='Gonzalez Gimenez').first()
            if not comp_gg:
                comp_gg = Competitor(name='Gonzalez Gimenez', url='https://www.gonzalezgimenez.com.py/')
                session.add(comp_gg)
            
            session.flush()

            def get_or_create_cp(comp_id, item):
                cp = session.query(CompetitorProduct).filter_by(
                    competitor_id=comp_id, name=item['name']
                ).first()
                if cp:
                    # Update potentially missing fields
                    if not cp.url and item.get('url'): cp.url = item.get('url')
                    if not cp.sku and item.get('sku'): cp.sku = item.get('sku')
                    if not cp.raw_brand and item.get('brand'): cp.raw_brand = item.get('brand')
                else:
                    btu = self._normalize_btu(item['name'])
                    inverter = self._is_inverter(item['name'])
                    cp = CompetitorProduct(
                        competitor_id=comp_id,
                        name=item['name'],
                        capacity_btu=btu,
                        is_inverter=inverter,
                        sku=item.get('sku'),
                        url=item.get('url'),
                        raw_brand=item.get('brand')
                    )
                    session.add(cp)
                    session.flush()
                return cp

            # Visuar acting as absolute canonical
            for v_item in visuar_data:
                cp_visuar = get_or_create_cp(comp_visuar.id, v_item)
                
                # Auto-approve canonical Visuar products
                if not cp_visuar.product_id:
                    db_product = Product(
                        name=v_item['name'],
                        capacity_btu=cp_visuar.capacity_btu,
                        is_inverter=cp_visuar.is_inverter,
                        brand=cp_visuar.raw_brand or "Identified",
                        description=cp_visuar.description
                    )
                    session.add(db_product)
                    session.flush()
                    cp_visuar.product_id = db_product.id
                    session.flush()

                session.add(PriceLog(
                    competitor_product_id=cp_visuar.id,
                    price=v_item['price'],
                    is_in_stock=True
                ))

            # Competitors (Staged for Human in loop mapping or AI)
            for b_item in bristol_data:
                cp_b = get_or_create_cp(comp_bristol.id, b_item)
                session.add(PriceLog(competitor_product_id=cp_b.id, price=b_item['price'], is_in_stock=True))

            if gg_data:
                for g_item in gg_data:
                    cp_g = get_or_create_cp(comp_gg.id, g_item)
                    session.add(PriceLog(competitor_product_id=cp_g.id, price=g_item['price'], is_in_stock=True))

            session.commit()
            logger.info("[PIPELINE_COMPLETE] Database synchronized. Staged raw data with pending suggestions.")

            # Run AI Product Matching
            logger.info("[AI_MATCHER] Starting Semantic DeepSeek Matching for unmatched products...")
            run_ai_matching(session)

            # Run Alert Engine
            from alert_engine import evaluate_alerts
            logger.info("[ALERT_ENGINE] Evaluating price alerts...")
            evaluate_alerts(session)
            
        except Exception as e:
            session.rollback()
            logger.error(f"[INTEGRITY_COMPROMISED] Transaction rolled back due to error: {e}", exc_info=True)
        finally:
            session.close()

    async def _run_targeted_deep_scrape(self):
        """Find CP without description and fetch it."""
        session = self.Session()
        try:
            unmatched = session.query(CompetitorProduct).filter(
                CompetitorProduct.description == None,
                CompetitorProduct.url != None
            ).all()
            
            if not unmatched: return
            
            logger.info(f"[DEEP_SCRAPE] Processing {len(unmatched)} items...")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                for cp in unmatched:
                    try:
                        logger.info(f"[DEEP_SCRAPE] Item: {cp.name}")
                        await page.goto(cp.url, wait_until="networkidle", timeout=20000)
                        
                        selectors = ['.product-description-short', '#product-desc-tab', '.caracteristicas', '.description']
                        content = None
                        for s in selectors:
                            el = await page.query_selector(s)
                            if el:
                                content = await el.inner_text()
                                if content: break
                        
                        if content:
                            cp.description = content.strip()
                        
                        # Also try SKU if missing
                        if not cp.sku:
                            ref_el = await page.query_selector('.product-reference')
                            if ref_el: cp.sku = (await ref_el.inner_text()).strip()
                            
                    except Exception as e:
                        logger.warning(f"[DEEP_SCRAPE] Skip {cp.url}: {e}")
                
                session.commit()
                await browser.close()
        finally:
            session.close()

if __name__ == "__main__":
    engine = MarketIntelligenceEngine()
    asyncio.run(engine.run_pipeline())
