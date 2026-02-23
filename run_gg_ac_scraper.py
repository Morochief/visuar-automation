import asyncio
import json
import os
from scraper_engine import ScraperEngine

async def main():
    engine = ScraperEngine()
    url = "https://www.gonzalezgimenez.com.py/categoria/127/acondicionadores-de-aire"
    
    print(f"Scraping category: {url}")
    products = await engine.scrape_gonzalez_gimenez(url)
    
    # Categorize by brand
    categorized = {}
    for p in products:
        brand = p.brand.upper()
        if brand not in categorized:
            categorized[brand] = []
        
        categorized[brand].append({
            "name": p.name,
            "price": p.price,
            "regular_price": p.regular_price,
            "btu": p.capacity_btu,
            "is_inverter": p.is_inverter
        })
        
    print(f"\nExtracted {len(products)} total products.")
    
    # Save the output to the frontend public directory for Astro to serve as JSON payload natively
    out_path = os.path.join("market_intelligence", "frontend_app", "public", "api")
    os.makedirs(out_path, exist_ok=True)
    json_path = os.path.join(out_path, "gg_ac_data.json")
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(categorized, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Data saved successfully to {json_path}")

if __name__ == "__main__":
    asyncio.run(main())
