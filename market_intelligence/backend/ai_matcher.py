"""
AI Product Matcher — Uses NVIDIA API (DeepSeek-v3.2) to intelligently
match competitor products to canonical Visuar products.

Replaces/complements the fuzzy-text matching with semantic understanding.
For example, identifies that "Samsung AR12BSHQAWK" and
"Aire Acond Samsung 12000 BTU Inverter" are the same product.

Usage:
    # As a standalone script
    python ai_matcher.py

    # Or imported and called from scraper.py
    from ai_matcher import run_ai_matching
    run_ai_matching(session)
"""
import json
import logging
import os
from typing import List, Optional

from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models import Base, Product, Competitor, CompetitorProduct, PendingMapping

logger = logging.getLogger("ai_matcher")

# ─── NVIDIA API Configuration ───────────────────────────────────────

NVIDIA_API_KEY = os.environ.get(
    "NVIDIA_API_KEY"
)

if not NVIDIA_API_KEY:
    raise ValueError(
        "NVIDIA_API_KEY environment variable is required for AI matching. "
        "Please set it in your .env file or deployment environment."
    )
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL = "deepseek-ai/deepseek-v3.2"

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/market_intel.db")

# ─── Prompt Engineering ─────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un experto en productos de Aires Acondicionados para el mercado paraguayo.
Tu tarea es realizar un matching строго(strict) entre productos de competidores y el catálogo de Visuar.

**REGLAS OBLIGATORIAS (NO puedes violar estas reglas):**
1. **MARCA IDÉNTICA**: El producto del competidor DEBE ser de la MISMA marca que el producto de Visuar.
   - Si el competidor es "Goodweather", solo puede matching con productos Goodweather de Visuar.
   - Si el competidor es "LG", solo puede matching con productos LG de Visuar.
   - Si el competidor es "Samsung", solo puede matching con productos Samsung de Visuar.
   - **CUALQUIER match con marca diferente es INCORRECTO y debe tener confidence 0%**.
2. **TIPO DE PRODUCTO**: El tipo debe coincidir:
   - Split/Pared solo con Split/Pared
   - Cassette solo con Cassette
   - Piso/Techo solo con Piso/Techo
   - Portátil solo con Portátil
3. **BTU**: Debe coincidir la capacidad (misma o muy similar).
4. **TECNOLOGÍA**: Inverter debe matching con Inverter.

**Ejemplos de matches INCORRECTOS (confidence = 0%):**
- Haustec → Goodweather = INCORRECTO (marcas diferentes)
- LG → Samsung = INCORRECTO (marcas diferentes)
- Oster → Midas = INCORRECTO (marcas diferentes)
- Split → Portátil = INCORRECTO (tipos diferentes)
- Split → Cassette = INCORRECTO (tipos diferentes)

**Ejemplos de matches CORRECTOS:**
- Goodweather 12000 Inverter → Goodweather 12000 Inverter = 95%+
- LG Artcool 18000 → LG Artcool 18000 = 95%+
- Midea 12000 → Midea 12000 = 90%+

Responde SIEMPRE en formato JSON válido."""

MATCH_PROMPT_TEMPLATE = """Analiza el siguiente producto del COMPETIDOR y busca la mejor coincidencia en nuestro CATÁLOGO.

**Producto del Competidor:**
- Nombre: {competitor_name}
- Marca (detectada): {competitor_brand}
- SKU/Ref: {competitor_sku}
- BTU: {competitor_btu}
- Inverter: {competitor_inverter}
- Descripción: {competitor_description}

**Candidatos del Catálogo Visuar:**
{candidates_text}

Responde con un JSON:
{{
    "best_match_id": <id o null>,
    "confidence": <0-100>,
    "reasoning": "<explica por qué coinciden marcas, btu, tecnología o códigos de modelo>"
}}"""


def _build_candidates_text(candidates: List[Product]) -> str:
    """Format canonical products as a numbered list for the prompt."""
    lines = []
    for c in candidates:
        inv = "Inverter" if c.is_inverter else "On/Off"
        desc_snippet = (c.description[:100] + "...") if c.description else "Sin descripción"
        lines.append(f"  #{c.id} | {c.name} | BTU: {c.capacity_btu} | {inv} | Marca: {c.brand} | Info: {desc_snippet}")
    return "\n".join(lines) if lines else "  (No hay candidatos)"


def _call_deepseek(prompt: str) -> Optional[dict]:
    """Send a prompt to the NVIDIA DeepSeek API and parse the JSON response."""
    try:
        client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)

        # Deep thinking mode via streaming for maximum accuracy
        completion = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            top_p=0.95,
            max_tokens=8192,
            extra_body={"chat_template_kwargs": {"thinking": True}},
            stream=True
        )

        # Collect streamed response
        raw_response = ""
        for chunk in completion:
            if not getattr(chunk, "choices", None):
                continue
            reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
            if reasoning:
                logger.debug(f"[AI_MATCHER] Thinking: {reasoning[:100]}...")
            if chunk.choices and chunk.choices[0].delta.content is not None:
                raw_response += chunk.choices[0].delta.content

        raw_response = raw_response.strip()

        # Strip markdown code fences if present
        if raw_response.startswith("```"):
            raw_response = raw_response.split("\n", 1)[1]
            if raw_response.endswith("```"):
                raw_response = raw_response[:-3].strip()

        result = json.loads(raw_response)
        return result

    except json.JSONDecodeError as e:
        logger.error(f"[AI_MATCHER] Failed to parse JSON response: {e}")
        logger.debug(f"[AI_MATCHER] Raw response: {raw_response}")
        return None
    except Exception as e:
        logger.error(f"[AI_MATCHER] API call failed: {e}")
        return None


def match_single_product(session: Session, cp: CompetitorProduct) -> Optional[dict]:
    """
    Use AI to find the best canonical match for a single competitor product.
    Returns the parsed AI response dict or None.
    """
    # Get candidate products with same BTU (narrow the search space)
    if cp.capacity_btu:
        candidates = session.query(Product).filter_by(capacity_btu=cp.capacity_btu).all()
    else:
        # If no BTU detected, get all products (last resort)
        candidates = session.query(Product).all()

    if not candidates:
        logger.info(f"[AI_MATCHER] No candidates for '{cp.name}' — skipping")
        return None

    prompt = MATCH_PROMPT_TEMPLATE.format(
        competitor_name=cp.name,
        competitor_brand=cp.raw_brand or "N/A",
        competitor_sku=cp.sku or "N/A",
        competitor_btu=cp.capacity_btu or "No detectado",
        competitor_inverter="Sí" if cp.is_inverter else "No",
        competitor_description=cp.description or "No disponible",
        candidates_text=_build_candidates_text(candidates),
    )

    result = _call_deepseek(prompt)

    if result:
        logger.info(
            f"[AI_MATCHER] '{cp.name}' → Match ID: {result.get('best_match_id')} "
            f"| Confidence: {result.get('confidence')}% "
            f"| Reason: {result.get('reasoning', 'N/A')}"
        )

    return result


def run_ai_matching(session: Session, min_confidence: int = 60):
    """
    Main entry point: find all unmatched competitor products and attempt
    AI-powered matching against the canonical catalog.

    Args:
        session: SQLAlchemy session
        min_confidence: Minimum AI confidence (0-100) required to create a PendingMapping
    """
    # Get competitor products without a canonical match
    unmatched = (
        session.query(CompetitorProduct)
        .filter(CompetitorProduct.product_id.is_(None))
        .all()
    )

    if not unmatched:
        logger.info("[AI_MATCHER] No unmatched products found. Nothing to do.")
        return

    logger.info(f"[AI_MATCHER] Processing {len(unmatched)} unmatched product(s)...")

    matched_count = 0
    skipped_count = 0
    failed_count = 0

    for cp in unmatched:
        result = match_single_product(session, cp)

        if not result:
            failed_count += 1
            continue

        best_match_id = result.get("best_match_id")
        if isinstance(best_match_id, str):
            best_match_id = best_match_id.strip("# ")
            if best_match_id.lower() == "none" or not best_match_id:
                best_match_id = None

        confidence = result.get("confidence", 0)

        if best_match_id and confidence >= min_confidence:
            # Verify the product ID actually exists
            canonical = session.query(Product).get(best_match_id)
            if not canonical:
                logger.warning(f"[AI_MATCHER] AI returned non-existent product ID {best_match_id}")
                failed_count += 1
                continue
            
            # Check brand matching before auto-approve
            competitor_brand = cp.raw_brand or ""
            visuar_brand = canonical.brand or ""
            brand_match = competitor_brand.lower().strip() == visuar_brand.lower().strip()
            
            # Only auto-apply if confidence is very high (>= 90) AND brands match
            if confidence >= 90 and brand_match:
                cp.product_id = best_match_id
                logger.info(f"[AI_MATCHER] AUTO-APPLIED match for '{cp.name}' (Confidence: {confidence}%, Brand match: {brand_match})")
            elif confidence >= 90 and not brand_match:
                logger.info(f"[AI_MATCHER] SKIPPED auto-apply for '{cp.name}' - brands don't match: '{competitor_brand}' vs '{visuar_brand}'")

            # Replace existing pending mapping
            session.query(PendingMapping).filter_by(competitor_product_id=cp.id).delete()
            session.add(PendingMapping(
                competitor_product_id=cp.id,
                suggested_product_id=best_match_id,
                match_score=confidence,
            ))
            matched_count += 1
        else:
            skipped_count += 1
            logger.debug(
                f"[AI_MATCHER] Low confidence ({confidence}%) for '{cp.name}' — skipping"
            )

    session.commit()
    logger.info(
        f"[AI_MATCHER] Complete. "
        f"Matched: {matched_count} | Skipped (low confidence): {skipped_count} | Failed: {failed_count}"
    )


# ─── Standalone Execution ───────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    )

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("=" * 60)
    print("  VISUAR AI Product Matcher (DeepSeek-v3.2)")
    print("=" * 60)
    print()

    run_ai_matching(session)
    session.close()
