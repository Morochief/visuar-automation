import asyncio
import json
import logging
import re
import time
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


async def retry_with_backoff(func, max_retries=3, base_delay=2):
    """
    Execute a function with exponential backoff retry logic.
    
    Args:
        func: The async function to execute
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds before first retry (default: 2)
    
    Returns:
        The result of the function, or raises the last exception if all retries fail
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 2, 4, 8 seconds
                logger.warning(f"[RETRY] Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"[RETRY] All {max_retries} attempts failed: {e}")
    if last_exception:
        raise last_exception
    raise Exception("Function failed without exceptions")

class MarketIntelligenceEngine:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.progress = {
            "current_source": "Idle",
            "current_item": 0,
            "total_items": 0,
            "phase": "Waiting",
            "percentage": 0
        }

    def _update_progress(self, source=None, current=None, total=None, phase=None):
        if source: self.progress["current_source"] = source
        if current is not None: self.progress["current_item"] = current
        if total is not None: self.progress["total_items"] = total
        if phase: self.progress["phase"] = phase
        
        if self.progress["total_items"] > 0:
            self.progress["percentage"] = round((self.progress["current_item"] / self.progress["total_items"]) * 100)
        else:
            self.progress["percentage"] = 0
        
        logger.info(f"[PROGRESS] {self.progress['phase']} | {self.progress['current_source']}: {self.progress['current_item']}/{self.progress['total_items']} ({self.progress['percentage']}%)")

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
                # Optimized Brand Extraction for GG
                # Example: "Acondicionador de Aire TOKYO ..." -> "TOKYO"
                parts = title.upper().split()
                brand = "UNKNOWN"
                
                # Brands observed: Altech, Goodweather, HITACHI, Mabe, Midas, Samsung, TCL, Tokyo, VCP, etc.
                known_brands = ["ALTECH", "GOODWEATHER", "HITACHI", "MABE", "MIDAS", "SAMSUNG", "TCL", "TOKYO", "VCP", "CARRIER", "LG", "MIDEA", "OSTER", "FAMA", "HAUSTEC", "WHIRLPOOL", "MITSUBISHI"]
                
                # Check for known brands anywhere in the title (case heavy)
                found_brand = False
                for b in known_brands:
                    if b in parts:
                        brand = b
                        found_brand = True
                        break
                
                if not found_brand and len(parts) > 0:
                    # Specific pattern for GG: "Acondicionador de Aire [BRAND] ..."
                    try:
                        if "AIRE" in parts:
                            idx = parts.index("AIRE")
                            if len(parts) > idx + 1:
                                potential = parts[idx + 1]
                                if potential not in ["SPLIT", "INVERTER", "PORTATIL", "PARED", "PISO", "VENTANA", "DE", "CON"]:
                                    brand = potential
                                    found_brand = True
                        
                        if not found_brand and "ACONDICIONADOR" in parts:
                            idx = parts.index("ACONDICIONADOR")
                            if len(parts) > idx + 1:
                                potential = parts[idx + 1]
                                if potential not in ["DE", "SPLIT", "AIRE"]:
                                    brand = potential
                                    found_brand = True
                    except: pass
                    
                    if not found_brand:
                        # Fallback to first non-generic word
                        generic_words = ["ACONDICIONADOR", "AIRE", "SPLIT", "INVERTER", "DE", "CON", "FRÍO", "CALOR"]
                        for word in parts:
                            if word not in generic_words and len(word) > 2:
                                brand = word
                                break

                results.append({
                    "name": title.strip(), 
                    "price": price,
                    "url": url,
                    "sku": None,
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
        
        # Update metadata for frontend timestamp
        self._update_metadata(len(visuar_data), len(gg_data), list(categorize(visuar_data).keys()), list(categorize(gg_data).keys()))

    def _update_metadata(self, visuar_count, gg_count, visuar_brands, gg_brands):
        """Update scrape_metadata.json with the latest run info."""
        metadata_path = os.path.join(JSON_OUTPUT_DIR, "scrape_metadata.json")
        metadata = {
            "last_scrape": datetime.now(timezone.utc).isoformat(),
            "visuar_count": visuar_count,
            "gg_count": gg_count,
            "visuar_brands": sorted(visuar_brands),
            "gg_brands": sorted(gg_brands)
        }
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"[EXPORT] Updated {metadata_path}")

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
                self._update_progress(source="Visuar", phase="Scraping", current=0, total=0)
                logger.info("Connecting to Visuar...")
                
                async def visit_visuar():
                    # STABLE BASELINE: Use resultsPerPage=9999999 to load all 73 products at once
                    await page.goto("https://www.visuar.com.py/hogar/aires-acondicionados/?resultsPerPage=9999999", wait_until="networkidle", timeout=60000)
                    
                    # Auto-pagination: While we have everything, we still scroll for lazy images/triggers
                    seen_urls = set()
                    all_results = []
                    
                    # Small wait for DOM items to render
                    await page.wait_for_selector('.product-miniature', timeout=20000)
                    
                    # Force a few scrolls to ensure everything is in state
                    for _ in range(3):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)
                    
                    current_results = await self._scraped_results_visuar(page)
                    for r in current_results:
                        if r["url"] not in seen_urls:
                            seen_urls.add(r["url"])
                            all_results.append(r)
                            
                    logger.info(f"[SOURCE_A] Visuar found {len(all_results)} items using 'View All' strategy.")
                    return all_results
                
                visuar_data = await retry_with_backoff(visit_visuar, max_retries=3)
                visuar_log.status = 'success'
                visuar_log.products_scraped = len(visuar_data)
                self._update_progress(source="Visuar", current=len(visuar_data), total=len(visuar_data))
                logger.info(f"[SOURCE_A] Ingested {len(visuar_data)} records from Visuar")
            except Exception as e:
                visuar_log.error_message = str(e)
                logger.error(f"[SOURCE_A] Visuar scrape failed: {e}")
            finally:
                visuar_log.finished_at = datetime.now(timezone.utc)
                session.add(visuar_log)
            
            # ── Bristol ──
            # DISABLED: User requested only GG scraping
            bristol_data = []
            bristol_log = ScrapeLog(started_at=datetime.now(timezone.utc), status='skipped')
            logger.info("[Bristol] Skipped - DISABLED by user request")
            session.add(bristol_log)

            # ── Gonzalez Gimenez ──
            gg_data = []
            gg_log = ScrapeLog(started_at=datetime.now(timezone.utc), status='failed')
            try:
                comp_g = session.query(Competitor).filter_by(name='Gonzalez Gimenez').first()
                if comp_g:
                    gg_log.competitor_id = comp_g.id
                self._update_progress(source="Gonzalez Gimenez", phase="Scraping", current=0, total=0)
                logger.info("Connecting to Gonzalez Gimenez...")
                # Set a more realistic User-Agent
                await context.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                })
                
                async def visit_gg():
                    await page.goto("https://www.gonzalezgimenez.com.py/categoria/127/acondicionadores-de-aire", wait_until="domcontentloaded")
                    try:
                        # Initial wait for JS to load
                        await page.wait_for_timeout(5000)
                        
                        # Multi-attempt popup bypass
                        for _ in range(3):
                            try:
                                close_selectors = [".ins-close-button", ".close-modal", ".modal-close", ".btn-close", ".pop-close"]
                                for selector in close_selectors:
                                    if await page.is_visible(selector):
                                        await page.click(selector, timeout=2000)
                                        logger.info(f"[GG_SCRAPE] Closed popup using {selector}")
                                        break
                                await page.keyboard.press("Escape")
                                await page.wait_for_timeout(1000)
                            except: pass

                        await page.wait_for_selector('.item-catalogo', timeout=60000)
                        
                        # Dynamic Infinite Scroll Loop
                        last_count = 0
                        stuck_count = 0
                        for i in range(50): # Max 50 attempts (~150s)
                            # Scroll by a larger increment
                            await page.evaluate("window.scrollBy(0, 3000)")
                            await page.wait_for_timeout(3000)
                            
                            items = await page.query_selector_all('.product.item-catalogo')
                            current_count = len(items)
                            self._update_progress(source="Gonzalez Gimenez", current=current_count, total=68, phase=f"Scrolling GG ({current_count}/68)")
                            
                            # Log progress
                            if i % 5 == 0:
                                logger.info(f"[GG_SCRAPE] Scroll {i}: Found {current_count} items...")

                            # Break if we see the end message or reach target
                            end_msg = await page.get_by_text("- Se llegó al final de la lista -").is_visible()
                            if end_msg or current_count >= 68:
                                logger.info(f"[GG_SCRAPE] End reached. Items: {current_count}")
                                break
                                
                            if current_count > last_count:
                                last_count = current_count
                                stuck_count = 0
                            else:
                                stuck_count += 1
                                # Shaking the scroll if stuck
                                if stuck_count >= 3:
                                    await page.evaluate("window.scrollBy(0, -1000)")
                                    await page.wait_for_timeout(1000)
                                    await page.evaluate("window.scrollBy(0, 2000)")
                                
                                if stuck_count > 6:
                                    logger.warning(f"[GG_SCRAPE] No new items after {stuck_count} scrolls. Stopping at {current_count}.")
                                    break
                            
                            # Standard scroll to bottom
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await page.wait_for_timeout(3000)
                            # Extra nudge to trigger lazy loader
                            await page.mouse.wheel(0, 1000)
                            await page.wait_for_timeout(2000)
                            
                    except Exception as e:
                        logger.warning(f"Error during GG infinite scroll: {e}")
                        await page.screenshot(path='/app/output/gg_debug.png')
                    return await self._scraped_results_gg(page)
                
                gg_data = await retry_with_backoff(visit_gg, max_retries=3)
                gg_log.status = 'success'
                gg_log.products_scraped = len(gg_data)
                self._update_progress(source="Gonzalez Gimenez", current=len(gg_data), total=len(gg_data), phase="Scraping Complete")
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

            total_sync = len(visuar_data) + len(bristol_data) + (len(gg_data) if gg_data else 0)
            self._update_progress(source="Database", phase="Syncing Data", current=0, total=total_sync)
            current_sync = 0

            def get_or_create_cp(comp_id, item):
                nonlocal current_sync
                current_sync += 1
                self._update_progress(current=current_sync)
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
            run_ai_matching(session, progress_callback=self._update_progress)

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
            self._update_progress(source="Deep Scrape", phase="Processing Details", current=0, total=len(unmatched))
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                for idx, cp in enumerate(unmatched):
                    try:
                        self._update_progress(current=idx + 1, total=len(unmatched))
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
