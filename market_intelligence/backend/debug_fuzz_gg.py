import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        print("Goto URL...")
        await page.goto("https://www.gonzalezgimenez.com.py/categoria/127/acondicionadores-de-aire", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        js = '''
        Array.from(document.querySelectorAll(".product")).slice(0, 3).map(p => p.innerHTML)
        '''
        res = await page.evaluate(js)
        with open("gg_debug_dom.txt", "w", encoding="utf-8") as f:
            for item in res:
                f.write(item + "\n\n=================================\n\n")
        
        print("Dumped 3 items to gg_debug_dom.txt")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
