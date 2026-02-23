import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = await context.new_page()
        
        url = "https://www.bristol.com.py/climatizacion/climatizacion/splits"
        print(f"Navigating to {url}")
        await page.goto(url, wait_until="networkidle")
        
        try:
            await page.wait_for_selector('.it', timeout=10000)
            print("Found '.it' selector.")
        except Exception as e:
            print("Timeout waiting for '.it' selector.")
        
        items = await page.query_selector_all('.it')
        print(f"Items found: {len(items)}")
        
        for i, item in enumerate(items[:3]):
            print(f"--- Item {i} ---")
            t_el = await item.query_selector('.info .tit h2')
            p_el = await item.query_selector('.precios .venta .monto')
            
            title = await t_el.inner_text() if t_el else "None"
            price = await p_el.inner_text() if p_el else "None"
            
            print(f"Title: {title}")
            print(f"Price: {price}")
            
            if not t_el or not p_el:
                html = await item.inner_html()
                print("HTML snippet inside item:", html[:500])
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
