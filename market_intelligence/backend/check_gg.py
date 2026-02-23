import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://www.gonzalezgimenez.com.py/categoria/127/acondicionadores-de-aire", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        js = '''
        Array.from(document.querySelectorAll(".product")).map(p => {
            const titleEl = p.querySelector(".product-title");
            const priceEl = p.querySelector(".product-price");
            return (titleEl ? titleEl.innerText : "") + " | " + (priceEl ? priceEl.innerText : "");
        })
        '''
        res = await page.evaluate(js)
        print("SELECTOR '.product':")
        for item in res:
            print(item)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
