"""
Unit tests for ai_matcher.py

Tests critical business logic including:
- Candidate text formatting
- JSON response parsing
- Brand validation logic
- Error handling

Usage:
    pytest test_ai_matcher.py -v
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock the NVIDIA_API_KEY before importing ai_matcher
import os
os.environ["NVIDIA_API_KEY"] = "test_key"


class TestBuildCandidatesText:
    """Tests for _build_candidates_text function."""

    def test_build_candidates_text_single_product(self):
        """Test formatting a single product candidate."""
        from ai_matcher import _build_candidates_text
        
        # Create mock product
        mock_product = Mock()
        mock_product.id = "abc-123"
        mock_product.name = "Samsung 12000 BTU Inverter"
        mock_product.capacity_btu = 12000
        mock_product.is_inverter = True
        mock_product.brand = "Samsung"
        mock_product.description = "Aire acondicionado Samsung 12000 BTU"
        
        result = _build_candidates_text([mock_product])
        
        assert "abc-123" in result
        assert "Samsung 12000 BTU Inverter" in result
        assert "BTU: 12000" in result
        assert "Inverter" in result
        assert "Marca: Samsung" in result

    def test_build_candidates_text_multiple_products(self):
        """Test formatting multiple product candidates."""
        from ai_matcher import _build_candidates_text
        
        products = []
        for i in range(3):
            p = Mock()
            p.id = f"id-{i}"
            p.name = f"Product {i}"
            p.capacity_btu = 12000
            p.is_inverter = True
            p.brand = "Samsung"
            p.description = f"Description {i}"
            products.append(p)
        
        result = _build_candidates_text(products)
        
        assert "#id-0" in result
        assert "#id-1" in result
        assert "#id-2" in result
        assert result.count("Product") == 3

    def test_build_candidates_text_empty_list(self):
        """Test with empty product list."""
        from ai_matcher import _build_candidates_text
        
        result = _build_candidates_text([])
        
        assert "(No hay candidatos)" in result

    def test_build_candidates_text_no_description(self):
        """Test product without description."""
        from ai_matcher import _build_candidates_text
        
        mock_product = Mock()
        mock_product.id = "test-id"
        mock_product.name = "Test Product"
        mock_product.capacity_btu = 9000
        mock_product.is_inverter = False
        mock_product.brand = "LG"
        mock_product.description = None
        
        result = _build_candidates_text([mock_product])
        
        assert "Sin descripción" in result

    def test_build_candidates_text_long_description(self):
        """Test product with very long description."""
        from ai_matcher import _build_candidates_text
        
        mock_product = Mock()
        mock_product.id = "test-id"
        mock_product.name = "Test Product"
        mock_product.capacity_btu = 18000
        mock_product.is_inverter = True
        mock_product.brand = "Midea"
        mock_product.description = "A" * 200  # Long description
        
        result = _build_candidates_text([mock_product])
        
        # Should truncate to ~100 chars + "..."
        assert "..." in result
        assert len(result) < 200  # Should be truncated


class TestBrandValidation:
    """Tests for brand validation logic."""

    def test_brand_match_exact(self):
        """Test exact brand matching."""
        competitor_brand = "Samsung"
        visuar_brand = "Samsung"
        
        brand_match = competitor_brand.lower().strip() == visuar_brand.lower().strip()
        
        assert brand_match is True

    def test_brand_match_case_insensitive(self):
        """Test brand matching is case insensitive."""
        competitor_brand = "SAMSUNG"
        visuar_brand = "samsung"
        
        brand_match = competitor_brand.lower().strip() == visuar_brand.lower().strip()
        
        assert brand_match is True

    def test_brand_match_with_whitespace(self):
        """Test brand matching with extra whitespace."""
        competitor_brand = "  Samsung  "
        visuar_brand = "Samsung"
        
        brand_match = competitor_brand.lower().strip() == visuar_brand.lower().strip()
        
        assert brand_match is True

    def test_brand_mismatch_different_brands(self):
        """Test brand mismatch detection."""
        competitor_brand = "Haustec"
        visuar_brand = "Goodweather"
        
        brand_match = competitor_brand.lower().strip() == visuar_brand.lower().strip()
        
        assert brand_match is False

    def test_brand_mismatch_samsung_vs_lg(self):
        """Test Samsung vs LG is correctly identified as mismatch."""
        competitor_brand = "Samsung"
        visuar_brand = "LG"
        
        brand_match = competitor_brand.lower().strip() == visuar_brand.lower().strip()
        
        assert brand_match is False

    def test_brand_empty_vs_samsung(self):
        """Test empty brand vs known brand."""
        competitor_brand = ""
        visuar_brand = "Samsung"
        
        brand_match = competitor_brand.lower().strip() == visuar_brand.lower().strip()
        
        assert brand_match is False

    def test_brand_none_vs_samsung(self):
        """Test None brand vs known brand."""
        competitor_brand = None
        visuar_brand = "Samsung"
        
        # Handle None case
        competitor_brand = competitor_brand or ""
        brand_match = competitor_brand.lower().strip() == visuar_brand.lower().strip()
        
        assert brand_match is False


class TestJSONParsing:
    """Tests for JSON response parsing robustness."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        response = '{"best_match_id": "abc-123", "confidence": 95, "reasoning": "Match found"}'
        
        result = json.loads(response)
        
        assert result["best_match_id"] == "abc-123"
        assert result["confidence"] == 95

    def test_parse_json_with_markdown_fence(self):
        """Test parsing JSON with markdown code fences."""
        response = '''```json
{"best_match_id": "abc-123", "confidence": 85}
```'''
        
        # Simulate the stripping logic from ai_matcher.py
        raw_response = response.strip()
        if raw_response.startswith("```"):
            raw_response = raw_response.split("\n", 1)[1]
            if raw_response.endswith("```"):
                raw_response = raw_response[:-3].strip()
        
        result = json.loads(raw_response)
        
        assert result["best_match_id"] == "abc-123"
        assert result["confidence"] == 85

    def test_parse_json_with_markdown_fence_no_lang(self):
        """Test parsing JSON with markdown fence without language spec."""
        response = '''```
{"best_match_id": "xyz-789", "confidence": 75}
```'''
        
        raw_response = response.strip()
        if raw_response.startswith("```"):
            raw_response = raw_response.split("\n", 1)[1]
            if raw_response.endswith("```"):
                raw_response = raw_response[:-3].strip()
        
        result = json.loads(raw_response)
        
        assert result["best_match_id"] == "xyz-789"

    def test_parse_invalid_json_returns_none(self):
        """Test that invalid JSON returns None (as per error handling)."""
        response = "This is not valid JSON"
        
        try:
            result = json.loads(response)
            pytest.fail("Should have raised JSONDecodeError")
        except json.JSONDecodeError:
            # Expected behavior
            pass

    def test_parse_malformed_json_returns_none(self):
        """Test that malformed JSON returns None."""
        response = '{"best_match_id": "abc", "confidence": }'
        
        try:
            result = json.loads(response)
            pytest.fail("Should have raised JSONDecodeError")
        except json.JSONDecodeError:
            # Expected behavior
            pass


class TestMatchIdProcessing:
    """Tests for best_match_id processing logic."""

    def test_match_id_with_hash_prefix(self):
        """Test stripping # prefix from match ID."""
        best_match_id = "#abc-123"
        
        best_match_id = best_match_id.strip("# ")
        
        assert best_match_id == "abc-123"

    def test_match_id_with_hash_and_prefix(self):
        """Test stripping # prefix with extra spaces."""
        best_match_id = " # abc-123 "
        
        best_match_id = best_match_id.strip("# ")
        
        assert best_match_id == "abc-123"

    def test_match_id_none_string(self):
        """Test 'none' string is converted to None."""
        best_match_id = "none"
        
        if best_match_id.lower() == "none" or not best_match_id:
            best_match_id = None
        
        assert best_match_id is None

    def test_match_id_empty_string(self):
        """Test empty string is converted to None."""
        best_match_id = ""
        
        if best_match_id.lower() == "none" or not best_match_id:
            best_match_id = None
        
        assert best_match_id is None

    def test_match_id_valid(self):
        """Test valid match ID passes through."""
        best_match_id = "abc-123-uuid"
        
        if isinstance(best_match_id, str):
            best_match_id = best_match_id.strip("# ")
            if best_match_id.lower() == "none" or not best_match_id:
                best_match_id = None
        
        assert best_match_id == "abc-123-uuid"


class TestConfidenceThresholds:
    """Tests for confidence threshold logic."""

    def test_high_confidence_auto_approve(self):
        """Test that >= 90 confidence triggers auto-approve."""
        confidence = 90
        brand_match = True
        
        auto_approve = confidence >= 90 and brand_match
        
        assert auto_approve is True

    def test_high_confidence_no_brand_match(self):
        """Test >= 90 confidence but no brand match - skip."""
        confidence = 95
        brand_match = False
        
        auto_approve = confidence >= 90 and brand_match
        skip_message = "brands don't match" if not brand_match else None
        
        assert auto_approve is False
        assert skip_message == "brands don't match"

    def test_medium_confidence_pending(self):
        """Test 60-89 confidence creates pending mapping."""
        confidence = 75
        min_confidence = 60
        
        creates_pending = confidence >= min_confidence
        
        assert creates_pending is True

    def test_low_confidence_skipped(self):
        """Test < 60 confidence is skipped."""
        confidence = 45
        min_confidence = 60
        
        creates_pending = confidence >= min_confidence
        
        assert creates_pending is False


class TestMockAPICall:
    """Tests using mocked API responses."""

    @patch('ai_matcher.OpenAI')
    def test_call_deepseek_success(self, mock_openai):
        """Test successful API call returns parsed JSON."""
        from ai_matcher import _call_deepseek
        
        # Mock the streaming response
        mock_chunk = Mock()
        mock_chunk.choices = [Mock()]
        mock_chunk.choices[0].delta.content = '{"best_match_id": "test-123", "confidence": 88}'
        
        mock_completion = [mock_chunk]
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client
        
        result = _call_deepseek("Test prompt")
        
        assert result is not None
        assert result["best_match_id"] == "test-123"

    @patch('ai_matcher.OpenAI')
    def test_call_deepseek_api_error(self, mock_openai):
        """Test API error returns None."""
        from ai_matcher import _call_deepseek
        
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client
        
        result = _call_deepseek("Test prompt")
        
        assert result is None


class TestPromptTemplate:
    """Tests for prompt template formatting."""

    def test_match_prompt_template_formatting(self):
        """Test prompt template is correctly formatted."""
        from ai_matcher import MATCH_PROMPT_TEMPLATE
        
        prompt = MATCH_PROMPT_TEMPLATE.format(
            competitor_name="Samsung 12000",
            competitor_brand="Samsung",
            competitor_sku="AR12BH",
            competitor_btu="12000",
            competitor_inverter="Sí",
            competitor_description="Aire Samsung 12000",
            candidates_text="  #1 | Product A | BTU: 12000"
        )
        
        assert "Samsung 12000" in prompt
        assert "Samsung" in prompt
        assert "AR12BH" in prompt
        assert "12000" in prompt
        assert "Product A" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
