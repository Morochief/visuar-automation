import asyncio
import logging
import re
from typing import Optional, List, Dict
from thefuzz import fuzz

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from playwright.async_api import async_playwright

from models import Base, Product, Competitor, PriceLog, CompetitorProduct, PendingMapping

DATABASE_URL = "sqlite:///market_intel.db"

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
        items = await page.query_selector_all('article.js-product-miniature')
        results = []
        for item in items:
            t_el = await item.query_selector('.product-title')
            p_el = await item.query_selector('.product-price')
            
            title = await t_el.inner_text() if t_el else ""
            price = 0.0
            if p_el:
                content = await p_el.get_attribute('content')
                if content:
                    try:
                        price = float(content)
                    except ValueError:
                        pass
            if title and price > 0:
                results.append({"name": title, "price": price})
        return results

    async def _scraped_results_bristol(self, page) -> list:
        items = await page.query_selector_all('#catalogoProductos .it')
        results = []
        for item in items:
            t_el = await item.query_selector('.info .tit h2')
            p_el = await item.query_selector('.precios .venta .monto')
            
            title = await t_el.inner_text() if t_el else ""
            price = 0.0
            if p_el:
                text = await p_el.inner_text()
                clean = text.upper().replace('GS', '').replace('.', '').replace(',', '').strip()
                try:
                    price = float(clean)
                except ValueError:
                    pass
            if title and price > 0:
                results.append({"name": title, "price": price})
        return results

    async def _scraped_results_gg(self, page) -> list:
        items = await page.query_selector_all('.product')
        results = []
        for item in items:
            t_el = await item.query_selector('.product-title')
            p_el = await item.query_selector('.product-price')
            
            title = await t_el.inner_text() if t_el else ""
            price = 0.0
            if p_el:
                text = await p_el.inner_text()
                clean = text.upper().replace('GS', '').replace('.', '').replace(',', '').strip()
                try:
                    price = float(clean)
                except ValueError:
                    pass
            if title and price > 0:
                results.append({"name": title, "price": price})
        return results

    async def run_pipeline(self):
        logger.info("[PIPELINE_START] Commencing Market Intelligence Data Ingestion")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
            page = await context.new_page()
            
            logger.info("Connecting to Visuar...")
            await page.goto("https://www.visuar.com.py/hogar/aires-acondicionados/", wait_until="networkidle")
            visuar_data = await self._scraped_results_visuar(page)
            logger.info(f"[SOURCE_A] Ingested {len(visuar_data)} records from Visuar")
            
            logger.info("Connecting to Bristol...")
            await page.goto("https://www.bristol.com.py/climatizacion/climatizacion/splits", wait_until="networkidle")
            try:
                await page.wait_for_selector('#catalogoProductos .it', timeout=10000)
                await page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning(f"Timeout waiting for elements on Bristol: {e}")
            
            bristol_data = await self._scraped_results_bristol(page)
            logger.info(f"[SOURCE_B] Ingested {len(bristol_data)} records from Bristol")
            
            logger.info("Connecting to Gonzalez Gimenez...")
            await page.goto("https://www.gonzalezgimenez.com.py/categoria/127/acondicionadores-de-aire", wait_until="networkidle")
            try:
                await page.wait_for_selector('.product', timeout=10000)
                await page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning(f"Timeout waiting for elements on GG: {e}")
            
            gg_data = await self._scraped_results_gg(page)
            logger.info(f"[SOURCE_C] Ingested {len(gg_data)} records from Gonzalez Gimenez")

            await browser.close()
            
        self._sync_to_database(visuar_data, bristol_data, gg_data)

    def _generate_pending_mapping(self, session, cp):
        if not cp.capacity_btu: return
        candidates = session.query(Product).filter_by(capacity_btu=cp.capacity_btu).all()
        best_match, best_score = None, 0
        for cand in candidates:
            score = fuzz.token_set_ratio(cp.name, cand.name)
            if score > best_score:
                best_score, best_match = score, cand
                
        if best_match and best_score > 35:
            # Overwrite previous pending mappings for this raw product
            session.query(PendingMapping).filter_by(competitor_product_id=cp.id).delete()
            session.add(PendingMapping(
                competitor_product_id=cp.id,
                suggested_product_id=best_match.id,
                match_score=best_score
            ))

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
                if not cp:
                    btu = self._normalize_btu(item['name'])
                    inverter = self._is_inverter(item['name'])
                    cp = CompetitorProduct(
                        competitor_id=comp_id,
                        name=item['name'],
                        capacity_btu=btu,
                        is_inverter=inverter
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
                        brand="Identified"
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

            # Competitors (Staged for Human in loop mapping)
            for b_item in bristol_data:
                cp_b = get_or_create_cp(comp_bristol.id, b_item)
                session.add(PriceLog(competitor_product_id=cp_b.id, price=b_item['price'], is_in_stock=True))
                
                if not cp_b.product_id:
                    self._generate_pending_mapping(session, cp_b)

            if gg_data:
                for g_item in gg_data:
                    cp_g = get_or_create_cp(comp_gg.id, g_item)
                    session.add(PriceLog(competitor_product_id=cp_g.id, price=g_item['price'], is_in_stock=True))
                    
                    if not cp_g.product_id:
                        self._generate_pending_mapping(session, cp_g)

            session.commit()
            logger.info("[PIPELINE_COMPLETE] Database synchronized. Staged raw data with pending suggestions.")
        except Exception as e:
            session.rollback()
            logger.error(f"[INTEGRITY_COMPROMISED] Transaction rolled back due to error: {e}", exc_info=True)
        finally:
            session.close()

if __name__ == "__main__":
    engine = MarketIntelligenceEngine()
    asyncio.run(engine.run_pipeline())
