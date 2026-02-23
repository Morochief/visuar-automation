import logging
from typing import List
from playwright.async_api import async_playwright, Page, BrowserContext
from matcher_logic import Product, normalize_btu, normalize_inverter

logger = logging.getLogger("soc_audit.scraper_engine")

class ScraperEngine:
    """Async web scraping boundaries powered by Playwright with stealth overrides."""
    
    async def _configure_stealth(self, context: BrowserContext) -> Page:
        """Inject runtime configurations to pass bot detection integrity checks."""
        page = await context.new_page()
        # await stealth_async(page)
        return page

    async def scrape_visuar(self, url: str) -> List[Product]:
        """
        Target: Source A (Visuar - PrestaShop)
        Node selectors: article.js-product-miniature, .product-title, .product-brand, content attr
        """
        logger.info(f"[EXTRACT_START] Commencing operation against Source A (Visuar): {url}")
        products: List[Product] = []
        seen_titles = set()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await self._configure_stealth(context)
            
            try:
                await page.goto(url, wait_until='networkidle')
                
                # Auto-pagination: Extract items, then click "Load More" or "Siguiente"
                while True:
                    await page.mouse.wheel(0, 2000) # Scroll down to trigger lazy load or reveal button
                    await page.wait_for_timeout(1000) # Let React/Prestashop breathe
                    
                    # Extract current page items
                    items = await page.query_selector_all('article.js-product-miniature')
                    for item in items:
                        title_el = await item.query_selector('.product-title')
                        brand_el = await item.query_selector('.product-brand')
                        price_el = await item.query_selector('.product-price')
                        regular_price_el = await item.query_selector('.regular-price')
                        
                        title = await title_el.inner_text() if title_el else ""
                        if not title or title in seen_titles:
                            continue
                            
                        seen_titles.add(title)
                        
                        brand = await brand_el.inner_text() if brand_el else "Unknown"
                        if not brand or brand == "Unknown":
                            brand_guess = title.split()[0].upper() if title else "Unknown"
                            brand = brand_guess if brand_guess in ['SAMSUNG', 'LG', 'MIDEA', 'JAM', 'WHIRLPOOL', 'CARRIER', 'TOKYO'] else brand
                        
                        price = 0.0
                        if price_el:
                            price_content = await price_el.get_attribute('content')
                            if price_content:
                                try:
                                    price = float(price_content)
                                except ValueError:
                                    pass
                                    
                        regular_price = None
                        if regular_price_el:
                            reg_price_text = await regular_price_el.inner_text()
                            clean_reg_price = reg_price_text.upper().replace('₲', '').replace('GS', '').replace('.', '').replace(',', '').strip()
                            try:
                                regular_price = float(clean_reg_price)
                            except ValueError:
                                pass
                                    
                        products.append(Product(
                            brand=brand,
                            capacity_btu=normalize_btu(title),
                            is_inverter=normalize_inverter(title),
                            price=price,
                            name=title,
                            source='Visuar',
                            regular_price=regular_price
                        ))
                        
                    try:
                        # Attempt to find the standard Prestashop pagination/infinite-scroll trigger
                        load_more = await page.query_selector('.next.js-search-link, .infinite-scroll-button')
                        if load_more and await load_more.is_visible():
                            await load_more.click()
                            await page.wait_for_timeout(3000) # Wait for network payload / page reload
                        else:
                            break # Reached the end of the catalog
                    except Exception:
                        break
                        
            except Exception as e:
                logger.error(f"[EXTRACT_FAULT] Source A execution dropped with exception: {str(e)}", exc_info=True)
            finally:
                await browser.close()
                
        logger.info(f"[EXTRACT_COMPLETE] Extracted {len(products)} entities from Source A.")
        return products

    async def scrape_bristol(self, url: str) -> List[Product]:
        """
        Target: Source B (Bristol - Fenicio)
        Node selectors: .it, .info .tit h2, .precios .venta .monto
        """
        logger.info(f"[EXTRACT_START] Commencing operation against Source B (Bristol): {url}")
        products: List[Product] = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await self._configure_stealth(context)
            
            try:
                await page.goto(url, wait_until='networkidle')
                items = await page.query_selector_all('.it')
                logger.info(f"[DATA_DISCOVERY] Surfaced {len(items)} DOM entity containers in Source B")
                
                for item in items:
                    title_el = await item.query_selector('.info .tit h2')
                    price_el = await item.query_selector('.precios .venta .monto')
                    
                    title = await title_el.inner_text() if title_el else ""
                    
                    price = 0.0
                    if price_el:
                        price_text = await price_el.inner_text()
                        # Sanitize typical currency payloads
                        clean_price = price_text.upper().replace('GS', '').replace('.', '').replace(',', '').strip()
                        try:
                            price = float(clean_price)
                        except ValueError:
                            pass
                            
                    if title:
                        products.append(Product(
                            brand="Unknown", # Implicitly unstated from selector parameters
                            capacity_btu=normalize_btu(title),
                            is_inverter=normalize_inverter(title),
                            price=price,
                            name=title,
                            source='Bristol'
                        ))
            except Exception as e:
                logger.error(f"[EXTRACT_FAULT] Source B execution dropped with exception: {str(e)}", exc_info=True)
            finally:
                await browser.close()
                
        logger.info(f"[EXTRACT_COMPLETE] Extracted {len(products)} entities from Source B.")
        return products

    async def scrape_gonzalez_gimenez(self, url: str) -> List[Product]:
        """
        Target: Source C (Gonzalez Gimenez)
        Node selectors: .product, .product-title, .current-price, .old-price-contado
        """
        logger.info(f"[EXTRACT_START] Commencing operation against Source C (Gonzalez Gimenez): {url}")
        products: List[Product] = []
        seen_titles = set()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await self._configure_stealth(context)
            
            try:
                await page.goto(url, wait_until='networkidle')
                
                # Infinite scroll logic: Scroll down until no new items are loaded
                previous_count = 0
                retries = 0
                
                while retries < 4:
                    await page.mouse.wheel(0, 4000)
                    await page.wait_for_timeout(1500)
                    
                    items = await page.query_selector_all('.product')
                    if len(items) == previous_count:
                        retries += 1
                    else:
                        retries = 0
                        previous_count = len(items)
                
                items = await page.query_selector_all('.product')
                logger.info(f"[DATA_DISCOVERY] Surfaced {len(items)} DOM entity containers in Source C after scrolling")
                
                for item in items:
                    title_el = await item.query_selector('.product-title')
                    # Refined selector to target the CASH (Contado) price specifically, avoiding installments
                    price_el = await item.query_selector('.btn-cart-contado .current-price')
                    
                    if not price_el:
                        price_el = await item.query_selector('.product-price .current-price')
                        
                    old_price_el = await item.query_selector('.old-price-contado')
                    if not old_price_el:
                         # Fallback if they use a generic class name inside the contado button
                         old_price_el = await item.query_selector('.btn-cart-contado .old-price')
                    
                    title = await title_el.inner_text() if title_el else ""
                    title = title.strip()
                    if not title or title in seen_titles:
                        continue
                        
                    seen_titles.add(title)
                    
                    # Improved brand extraction: look for known brands in the title string
                    title_upper = title.upper()
                    known_brands = [
                        'SAMSUNG', 'LG', 'MIDEA', 'JAM', 'WHIRLPOOL', 'CARRIER', 'TOKYO', 'MIDAS', 
                        'GOODWEATHER', 'TCL', 'SPEED', 'MUELLER', 'ELECTROLUX', 'ALTECH', 'HITACHI', 
                        'MABE', 'VCP', 'CONTINENTAL', 'AURORA', 'CONSUL'
                    ]
                    brand = "Unknown"
                    for b in known_brands:
                        if b in title_upper:
                            brand = b
                            break
                    
                    price = 0.0
                    if price_el:
                        price_text = await price_el.inner_text()
                        # Sanitize: Remove everything that isn't a digit
                        import re
                        clean_price = re.sub(r'[^\d]', '', price_text)
                        try:
                            price = float(clean_price)
                        except ValueError:
                            pass
                            
                    regular_price = None
                    if old_price_el:
                        old_price_text = await old_price_el.inner_text()
                        clean_old_price = re.sub(r'[^\d]', '', old_price_text)
                        try:
                            regular_price = float(clean_old_price)
                        except ValueError:
                            pass
                            
                    if title and price > 0:
                        products.append(Product(
                            brand=brand,
                            capacity_btu=normalize_btu(title),
                            is_inverter=normalize_inverter(title),
                            price=price,
                            name=title,
                            source='Gonzalez Gimenez',
                            regular_price=regular_price
                        ))
            except Exception as e:
                logger.error(f"[EXTRACT_FAULT] Source C execution dropped with exception: {str(e)}", exc_info=True)
            finally:
                await browser.close()
                
        logger.info(f"[EXTRACT_COMPLETE] Extracted {len(products)} entities from Source C.")
        return products
