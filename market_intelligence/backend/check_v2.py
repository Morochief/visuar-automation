import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://www.visuar.com.py/")
        await page.wait_for_selector('a', timeout=10000)
        
        js = '''
        Array.from(document.querySelectorAll("a")).map(a => a.innerText + " -> " + a.href).filter(t => t.toLowerCase().includes("aire") || t.toLowerCase().includes("climat") || t.toLowerCase().includes("split"))
        '''
        links = await page.evaluate(js)
        print("\n".join(links))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
