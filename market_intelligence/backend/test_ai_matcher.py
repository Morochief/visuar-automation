"""
Unit test for the AI Matcher.
Mocks the NVIDIA API call to test the prompt generation and JSON parsing logic.
"""
import os
import sys
import json
from unittest.mock import patch

# Ensure local imports work
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Product, Competitor, CompetitorProduct, PendingMapping
from ai_matcher import run_ai_matching, match_single_product, _build_candidates_text

TEST_DB_URL = "sqlite:///:memory:"

def setup_test_db():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def test_build_candidates_text():
    """Verify that canonical products are formatted correctly for the prompt."""
    p1 = Product(id=1, name="Visuar AC", capacity_btu=12000, is_inverter=True, brand="Visuar")
    p2 = Product(id=2, name="Visuar Standard AC", capacity_btu=9000, is_inverter=False, brand="Visuar")
    
    text = _build_candidates_text([p1, p2])
    assert "#1 — Visuar AC | BTU: 12000 | Inverter: Sí" in text
    assert "#2 — Visuar Standard AC | BTU: 9000 | Inverter: No" in text
    print("✅ Candidates text formatted correctly.")

@patch('ai_matcher._call_deepseek')
def test_match_single_product(mock_call):
    """Verify that the matching function processes the AI response correctly."""
    session = setup_test_db()
    
    # Mock the API response
    mock_call.return_value = {
        "best_match_id": 1,
        "confidence": 95,
        "reasoning": "Same brand, BTU, and inverter status."
    }
    
    prod = Product(id=1, name="Visuar AC", capacity_btu=12000, is_inverter=True, brand="Visuar")
    session.add(prod)
    session.commit()
    
    cp = CompetitorProduct(name="Competitor AC 12K Inv", capacity_btu=12000, is_inverter=True)
    result = match_single_product(session, cp)
    
    assert result is not None
    assert result["best_match_id"] == 1
    assert result["confidence"] == 95
    print("✅ Single product match parses AI response correctly.")

@patch('ai_matcher.match_single_product')
def test_run_ai_matching(mock_match):
    """Verify that the main loop processes unmatched items and creates PendingMappings."""
    session = setup_test_db()
    
    # Setup mock canonical product
    prod = Product(id=10, name="Target Canonical AC", capacity_btu=12000)
    session.add(prod)
    
    # Setup unmatched competitor product
    comp = Competitor(id=1, name="Test", url="http://test.com")
    cp = CompetitorProduct(id=1, competitor_id=1, name="Unmatched AC", capacity_btu=12000)
    session.add(comp)
    session.add(cp)
    session.commit()
    
    # Mock the AI matching result a strong match
    mock_match.return_value = {
        "best_match_id": 10,
        "confidence": 85,
        "reasoning": "Strong match."
    }
    
    run_ai_matching(session, min_confidence=60)
    
    # Verify PendingMapping was created
    mappings = session.query(PendingMapping).all()
    assert len(mappings) == 1
    assert mappings[0].competitor_product_id == 1
    assert mappings[0].suggested_product_id == 10
    assert mappings[0].match_score == 85
    print("✅ Main loop creates PendingMappings correctly.")

if __name__ == "__main__":
    print("Running AI Matcher Tests...")
    test_build_candidates_text()
    test_match_single_product()
    test_run_ai_matching()
    print("All tests passed! 🎉")
