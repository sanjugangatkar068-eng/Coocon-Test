"""
Unit tests for AI Response Parsing & Error Handling (tests/test_ai_parsing_and_errors.py)
"""

import pytest
from PIL import Image
from image_analysis import (
    clean_json_response,
    parse_and_validate_ai_json,
    analyze_cocoon_image,
)


def test_clean_json_response_with_markdown_fences():
    """Verify that JSON wrapped in ```json ... ``` is correctly extracted."""
    raw = """
    Here is the inspection output:
    ```json
    {
      "is_cocoon": true,
      "evidence_sufficient": true,
      "shape_uniformity_score": 88
    }
    ```
    Thank you for using the sericulture system.
    """
    cleaned = clean_json_response(raw)
    assert cleaned.startswith("{")
    assert cleaned.endswith("}")
    assert '"shape_uniformity_score": 88' in cleaned


def test_clean_json_response_without_fences():
    """Verify parsing when output contains raw JSON with leading/trailing text."""
    raw = 'Analysis result: {"is_cocoon": true, "cocoon_count": 2}'
    cleaned = clean_json_response(raw)
    assert cleaned == '{"is_cocoon": true, "cocoon_count": 2}'


def test_parse_empty_model_response():
    """Verify handling when the model returns an empty string."""
    success, data, err_msg = parse_and_validate_ai_json("")
    assert success is False
    assert "empty" in err_msg.lower()
    assert data == {}


def test_parse_invalid_json_syntax():
    """Verify handling when the model returns broken / malformed JSON."""
    broken_json = '{"is_cocoon": true, "shape_uniformity_score": 85,'  # Missing closing brace
    success, data, err_msg = parse_and_validate_ai_json(broken_json)
    assert success is False
    assert "Failed to parse model JSON" in err_msg
    assert data == {}


def test_missing_api_credentials_handling():
    """
    Verify that calling analysis with a missing API key returns a clear setup
    instruction instead of crashing or leaking exceptions.
    """
    dummy_img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    success, data, err_msg = analyze_cocoon_image(
        image=dummy_img,
        api_key="",  # Blank key
    )

    assert success is False
    assert "SARVAM_API_KEY is not configured" in err_msg
    assert "dashboard.sarvam.ai" in err_msg
    assert data == {}


def test_dummy_placeholder_api_key_handling():
    """Verify that the unedited template key is caught as unconfigured."""
    dummy_img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    success, data, err_msg = analyze_cocoon_image(
        image=dummy_img,
        api_key="your_sarvam_api_key_here",
    )

    assert success is False
    assert "not configured" in err_msg.lower()
