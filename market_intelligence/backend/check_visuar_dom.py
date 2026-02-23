import asyncio
import json
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        print("Fetching Visuar...")
        await page.goto("https://www.visuar.com.py/electrodomesticos/climatizacion/aires-acondicionados", wait_until="networkidle")
        
        script = """() => {
            const items = document.querySelectorAll('article.js-product-miniature');
            return Array.from(items).map(i => {
                const title = i.querySelector('.product-title').innerText;
                const parent1 = i.parentElement ? i.parentElement.className : 'NONE';
                const parent2 = i.parentElement && i.parentElement.parentElement ? i.parentElement.parentElement.className : 'NONE';
                const parent3 = i.parentElement && i.parentElement.parentElement && i.parentElement.parentElement.parentElement ? i.parentElement.parentElement.parentElement.className : 'NONE';
                const parent4 = i.parentElement && i.parentElement.parentElement && i.parentElement.parentElement.parentElement && i.parentElement.parentElement.parentElement.parentElement ? i.parentElement.parentElement.parentElement.parentElement.id : 'NONE';
                return {title: title, p1: parent1, p2: parent2, p3: parent3, p4: parent4};
            });
        }"""
        
        res = await page.evaluate(script)
        with open("dom_structure.json", "w", encoding="utf-8") as f:
            json.dump(res, f, indent=4)
        
        print("Wrote dom_structure.json")
        await browser.close()
        
if __name__ == '__main__':
    asyncio.run(run())
