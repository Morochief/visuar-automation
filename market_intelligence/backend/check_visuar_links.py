import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = await context.new_page()
        
        url = "https://www.visuar.com.py/"
        print(f"Navigating to {url}")
        await page.goto(url, wait_until="networkidle")
        
        links = await page.query_selector_all('a')
        for link in links:
            text = await link.inner_text()
            href = await link.get_attribute('href')
            if href and 'climatizacion' in href.lower():
                print(f"Found: {text.strip()} -> {href}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
