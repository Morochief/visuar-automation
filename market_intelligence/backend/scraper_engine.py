import asyncio
import re
from playwright.async_api import async_playwright
from thefuzz import fuzz, process
from typing import List, Dict, Any

class ProductNormalizer:
    @staticmethod
    def extract_btu(raw_name: str) -> int:
        match = re.search(r'(\d{1,2}(?:\.\d{3})?|\d{1,2}k)\s*(btu)?', raw_name.lower())
        if match:
            val = match.group(1).replace('.', '')
            if 'k' in val: return int(val.replace('k', '')) * 1000
            if len(val) <= 2: return int(val) * 1000
            return int(val)
        return None

    @staticmethod
    def is_inverter(raw_name: str) -> bool:
        return 'inverter' in raw_name.lower() or 'inv' in raw_name.lower()

class SmartMatcher:
    def __init__(self, master_products_dict: Dict[int, str]):
        # Example format: {1: "Split Samsung 12000 BTU Inverter", 45: "Split MDV 18000 BTU"}
        self.masters = master_products_dict

    def get_match(self, raw_name: str, threshold: int = 85) -> Dict[str, Any]:
        """
        Calculates the best match for a scraped raw name against the master product database.
        Returns the match details, status, and confidence score.
        """
        if not self.masters:
            return {"master_id": None, "confidence": 0, "suggested": None, "status": "NO_MASTERS_AVAILABLE"}

        clean_target = re.sub(r'[^a-zA-Z0-9\s]', '', raw_name.lower())
        choices = {k: re.sub(r'[^a-zA-Z0-9\s]', '', v.lower()) for k, v in self.masters.items()}
        
        # Token set ratio is ideal for jumbled product names
        best_match_str, score, best_match_id = process.extractOne(
            clean_target, 
            choices, 
            scorer=fuzz.token_set_ratio
        )
        
        if score >= threshold:
            return {
                "master_id": best_match_id, 
                "confidence": score, 
                "status": "AUTO_MATCHED"
            }
                    
        return {
            "master_id": None, 
            "confidence": score, 
            "suggested": best_match_str, 
            "suggested_id": best_match_id,
            "status": "REQUIRES_HUMAN_REVIEW"
        }

class ScraperEngine:
    async def run(self):
        print("[*] Starting asynchronous market intelligence scraper...")
        scraped_data = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # --- SCRAPE VISUAR ---
            try:
                print("[*] Scraping Visuar...")
                await page.goto("https://visuar.com.py/climatizacion/aires-acondicionados")
                await page.wait_for_selector('.js-product-miniature', timeout=10000)
                visuar_items = await page.query_selector_all('.js-product-miniature')
                print(f"[+] Found {len(visuar_items)} products on Visuar")

                for item in visuar_items:
                    title_el = await item.query_selector('.product-title a')
                    price_el = await item.query_selector('.product-price')
                    brand_el = await item.query_selector('.product-brand')
                    url_el = await item.query_selector('.product-title a')

                    if title_el:
                        title = await title_el.inner_text()
                        url = await url_el.get_attribute('href') if url_el else ""
                        brand = await brand_el.inner_text() if brand_el else "Unknown"
                        
                        price = 0.0
                        if price_el:
                            price_text = await price_el.inner_text()
                            clean_price = price_text.replace('Gs.', '').replace('.', '').replace(',', '').strip()
                            try:
                                price = float(clean_price)
                            except ValueError:
                                pass
                        
                        scraped_data.append({
                            "competitor": "Visuar",
                            "raw_name": title,
                            "brand": brand,
                            "price": price,
                            "url": url,
                            "btu": ProductNormalizer.extract_btu(title),
                            "inverter": ProductNormalizer.is_inverter(title)
                        })
            except Exception as e:
                print(f"[-] Error scraping Visuar: {e}")

            # --- SCRAPE BRISTOL ---
            try:
                print("[*] Scraping Bristol...")
                await page.goto("https://www.bristol.com.py/electrodomesticos/climatizacion")
                await page.wait_for_selector('.it', timeout=10000)
                bristol_items = await page.query_selector_all('.it')
                print(f"[+] Found {len(bristol_items)} products on Bristol")

                for item in bristol_items:
                    title_el = await item.query_selector('.info .tit h2')
                    price_el = await item.query_selector('.precios .venta .monto')
                    url_el = await item.query_selector('.info .tit a')

                    if title_el:
                        title = await title_el.inner_text()
                        url = await url_el.get_attribute('href') if url_el else ""
                        
                        price = 0.0
                        if price_el:
                            price_text = await price_el.inner_text()
                            clean_price = price_text.upper().replace('GS', '').replace('.', '').replace(',', '').strip()
                            try:
                                price = float(clean_price)
                            except ValueError:
                                pass
                        
                        scraped_data.append({
                            "competitor": "Bristol",
                            "raw_name": title,
                            "brand": "Unknown", # Requires further NLP or brand dictionary
                            "price": price,
                            "url": url,
                            "btu": ProductNormalizer.extract_btu(title),
                            "inverter": ProductNormalizer.is_inverter(title)
                        })

            except Exception as e:
                print(f"[-] Error scraping Bristol: {e}")
            
            await browser.close()
        
        return scraped_data

if __name__ == "__main__":
    # Example execution
    engine = ScraperEngine()
    results = asyncio.run(engine.run())
    for r in results[:5]:
        print(r)
