import asyncio
from playwright.async_api import async_playwright
from thefuzz import fuzz
from scraper import MarketIntelligenceEngine
import logging

logging.disable(logging.CRITICAL)

async def run():
    engine = MarketIntelligenceEngine()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.visuar.com.py/electrodomesticos/climatizacion/aires-acondicionados")
        visuar_data = await engine._scraped_results_visuar(page)
        
        await page.goto("https://www.bristol.com.py/climatizacion/climatizacion/splits")
        await page.wait_for_selector('#catalogoProductos .it', timeout=10000)
        bristol_data = await engine._scraped_results_bristol(page)
        
        print(f"Visuar total items: {len(visuar_data)}")
        print(f"Bristol total items: {len(bristol_data)}")
        
        for v in visuar_data[:5]:
            btu = engine._normalize_btu(v['name'])
            print(f"Visuar: '{v['name']}' -> BTU: {btu}")
            best_match, best_score = None, 0
            for b in bristol_data:
                b_btu = engine._normalize_btu(b['name'])
                if b_btu == btu:
                    score = fuzz.token_set_ratio(v['name'], b['name'])
                    if score > best_score:
                        best_score, best_match = score, b
            if best_match:
                print(f"  Best Bristol Match: '{best_match['name']}' | Score: {best_score}")
        await browser.close()
        
if __name__ == '__main__':
    asyncio.run(run())
