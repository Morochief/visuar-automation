import asyncio
import json
import logging
import sys
from scraper_engine import ScraperEngine
from matcher_logic import MatchingEngine

# Enterprise Logging Configuration tailored for SOC Analyst 
# (Log Analytics, Identity & Integrity Event tracing)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | SOC-AUDIT | [%(name)s] | %(message)s',
    handlers=[
        logging.FileHandler("soc_data_integrity.log", mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("app.orchestrator")

async def main():
    logger.info("[ORCHESTRATOR_INIT] Launching secure price correlation pipeline.")
    
    # Provision components
    engine = ScraperEngine()
    matcher = MatchingEngine(threshold=90)
    
    # Replace URLs with the specific product layout directories based on platform taxonomy
    url_visuar = "https://www.visuar.com.py/" 
    url_bristol = "https://www.bristol.com.py/"
    
    logger.info("[PIPELINE_PHASE] Commencing Source A ingestion")
    visuar_products = await engine.scrape_visuar(url_visuar)
    
    logger.info("[PIPELINE_PHASE] Commencing Source B ingestion")
    bristol_products = await engine.scrape_bristol(url_bristol)
    
    logger.info("[PIPELINE_PHASE] Invoking correlation heuristics")
    final_payload = matcher.compare(visuar_products, bristol_products)
    
    output_target = "comparison_results.json"
    logger.info(f"[DATA_EXPORT] Flushing correlation payload to structured registry: {output_target}")
    
    with open(output_target, "w", encoding="utf-8") as file_out:
        json.dump(final_payload, file_out, indent=4, ensure_ascii=False)
        
    logger.info("[ORCHESTRATOR_TERMINATE] Job executed with successful payload delivery.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("[PIPELINE_INTERRUPT] Aborted via administrative local signal (SIGINT).")
    except Exception as exc:
        logger.error(f"[PIPELINE_CRITICAL] Unhandled orchestrator failure: {exc}", exc_info=True)
