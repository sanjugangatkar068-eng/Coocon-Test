"""
Unit tests for the Sarvam AI vision provider wiring (tests/test_sarvam_provider.py).

These tests mock the network so they run offline and never touch a real API key.
"""

import pytest
from PIL import Image
import image_analysis
from image_analysis import (
    analyze_cocoon_image,
    resolve_model_name,
    _image_to_data_uri,
)


class FakeResp:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text

    def json(self):
        if self._body is None:
            raise ValueError("no json body")
        return self._body


def _good_body(content: str):
    return {"choices": [{"message": {"content": content}}]}


VALID_JSON = (
    '{"is_cocoon": true, "evidence_sufficient": true, "shape_uniformity_score": 88, '
    '"compactness_score": 90, "cleanliness_score": 91, "defects_detected": [], '
    '"color_type": "White (Bivoltine)", "cocoon_count": 1, '
    '"visual_observations": ["Oval firm cocoon"], "recommendations": ["Store dry"]}'
)


def _no_network_models(monkeypatch):
    monkeypatch.setattr(image_analysis, "list_available_models", lambda api_key=None: [])


def test_successful_analysis_sends_inline_image_and_parses(monkeypatch):
    _no_network_models(monkeypatch)
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResp(200, _good_body(VALID_JSON))

    monkeypatch.setattr(image_analysis.requests, "post", fake_post)

    img = Image.new("RGB", (120, 120), (255, 255, 255))
    ok, data, err = analyze_cocoon_image(img, api_key="sk_test_1234567890", model_name="gemma4")

    assert ok is True
    assert err == ""
    assert data["is_cocoon"] is True
    assert data["_model_used"] == "gemma4"

    # Auth header uses the Sarvam convention
    assert captured["headers"]["api-subscription-key"] == "sk_test_1234567890"

    # The request targets Sarvam's v2 chat completions endpoint
    assert "sarvam.ai" in captured["url"]

    # The image is sent as an inline base64 data URI (remote URLs are rejected)
    parts = captured["json"]["messages"][0]["content"]
    image_parts = [p for p in parts if p.get("type") == "image_url"]
    assert image_parts, "expected an image_url content part"
    assert image_parts[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert captured["json"]["model"] == "gemma4"


def test_missing_key_reports_clear_error():
    img = Image.new("RGB", (100, 100))
    ok, data, err = analyze_cocoon_image(img, api_key="")
    assert ok is False
    assert "SARVAM_API_KEY is not configured" in err


def test_placeholder_key_is_rejected():
    img = Image.new("RGB", (100, 100))
    ok, data, err = analyze_cocoon_image(img, api_key="your_sarvam_api_key_here")
    assert ok is False
    assert "not configured" in err.lower()


def test_auth_error_is_mapped_to_clear_message(monkeypatch):
    _no_network_models(monkeypatch)
    monkeypatch.setattr(
        image_analysis.requests, "post",
        lambda *a, **k: FakeResp(403, {"error": {"message": "invalid api key"}}),
    )
    img = Image.new("RGB", (100, 100))
    ok, data, err = analyze_cocoon_image(img, api_key="sk_bad_key_1234567890")
    assert ok is False
    assert "rejected" in err.lower() or "auth" in err.lower()


def test_rate_limit_is_mapped(monkeypatch):
    _no_network_models(monkeypatch)
    monkeypatch.setattr(image_analysis.requests, "post", lambda *a, **k: FakeResp(429, {"error": "slow down"}))
    img = Image.new("RGB", (100, 100))
    ok, data, err = analyze_cocoon_image(img, api_key="sk_test_1234567890")
    assert ok is False
    assert "rate limit" in err.lower()


def test_text_only_model_falls_back_to_vision_model(monkeypatch):
    _no_network_models(monkeypatch)
    name, note = resolve_model_name(api_key="sk_test_1234567890", requested="sarvam-105b")
    assert name == "gemma4"
    assert "text-only" in note.lower()


def test_image_to_data_uri_prefix():
    img = Image.new("RGB", (64, 64), (10, 20, 30))
    uri = _image_to_data_uri(img)
    assert uri.startswith("data:image/jpeg;base64,")
    assert len(uri) > 50
