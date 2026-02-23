import re
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Union
from thefuzz import fuzz

logger = logging.getLogger("soc_audit.matcher_logic")

@dataclass
class Product:
    brand: str
    capacity_btu: Optional[int]
    is_inverter: bool
    price: float
    # Extra attributes for matching logic
    name: str = ""
    source: str = ""
    regular_price: Optional[float] = None

def normalize_btu(title: str) -> Optional[int]:
    """
    Extracts BTU capacity from string using regex.
    Matches forms like '18000', '18000btu', '18k', '18 k', '18.000'.
    """
    title_lower = title.lower()
    # Remove dots from numbers in the title for easier matching (e.g. 18.000 -> 18000)
    title_norm = re.sub(r'(\d)\.(\d{3})', r'\1\2', title_lower)
    
    # Identifies values followed by 'k' or 'btu'
    match = re.search(r'(\d{1,5})\s*(k|btu)', title_norm)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if unit == 'k' or val <= 60:
            return val * 1000
        return val
        
    # Fallback to direct numeric representations often found in air conditioners
    match_exact = re.search(r'\b(9000|12000|18000|24000|30000|36000|60000)\b', title_norm)
    if match_exact:
        return int(match_exact.group(1))
        
    return None

def normalize_inverter(title: str) -> bool:
    """Validates if the product is inverter."""
    return 'inverter' in title.lower()

class MatchingEngine:
    def __init__(self, threshold: int = 90):
        self.threshold = threshold
        
    def compare(self, products_a: List[Product], products_b: List[Product]) -> List[Dict[str, Union[str, float]]]:
        """
        Cross-comparison logic using thefuzz.token_set_ratio.
        Source A products matched against Source B.
        """
        results = []
        logger.info(f"[DATA_INTEGRITY] Initiating matching engine: Source A ({len(products_a)}) vs Source B ({len(products_b)})")
        
        for p_a in products_a:
            best_match: Optional[Product] = None
            best_score = 0
            
            for p_b in products_b:
                # Rule 1: Technical Attribute Validations - BTU match
                if p_a.capacity_btu == p_b.capacity_btu and p_a.capacity_btu is not None:
                    # Rule 2: Token-based similarity threshold
                    score = fuzz.token_set_ratio(p_a.name, p_b.name)
                    if score > self.threshold and score > best_score:
                        best_score = score
                        best_match = p_b
                            
            if best_match:
                logger.info(f"[MATCH_FOUND] Identity match confirmed: '{p_a.name}' (A) <=> '{best_match.name}' (B) | Score: {best_score}")
                
                diff_percent = 0.0
                if p_a.price is not None and p_a.price > 0 and best_match.price is not None:
                    # Diff percentage format requested in output structure
                    diff_percent = ((best_match.price - p_a.price) / p_a.price) * 100

                results.append({
                    "producto": p_a.name,
                    "visuar_price": p_a.price,
                    "bristol_price": best_match.price,
                    "diff_percent": round(diff_percent, 2)
                })
                
        logger.info(f"[PROCESS_COMPLETE] Matching engine finished processing payload. Yielding {len(results)} paired identities.")
        return results
