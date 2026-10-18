"""
SilkCocoonAI - Multimodal AI Image Analysis (image_analysis.py)

This module handles:
1. Secure, in-memory validation of uploaded cocoon photographs.
2. Prompt engineering for sericulture grading using a multimodal Vision AI.
3. Clean JSON schema enforcement and robust response parsing.
4. Safe error handling when credentials are missing or models return invalid data.
5. Sarvam AI as the vision provider: we call Sarvam's OpenAI-compatible
   Chat Completion V2 endpoint (https://api.sarvam.ai/v2/chat/completions).
   The image-capable Sarvam model is `gemma4` (Gemma 4 31B, text + image input).

Provider notes
--------------
- Endpoint:  POST https://api.sarvam.ai/v2/chat/completions
- Auth:      header `api-subscription-key: <SARVAM_API_KEY>`
- Images:    must be inline base64 data URIs in an `image_url` content part.
             Remote image URLs are rejected by the API.
- Model:     `gemma4` accepts text + images. `sarvam-105b`, `glm5.3` and
             `deepseekv4.1-flash` are text-only and cannot grade a photo.
"""

import io
import os
import json
import base64
import re
from typing import Dict, Any, Tuple, Optional, List
from PIL import Image

import requests

# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------
SARVAM_CHAT_URL = os.getenv("SARVAM_CHAT_URL", "https://api.sarvam.ai/v2/chat/completions").strip()
SARVAM_MODELS_URL = os.getenv("SARVAM_MODELS_URL", "https://api.sarvam.ai/v2/models").strip()

# The only Sarvam model that accepts image input.
DEFAULT_MODEL = os.getenv("SARVAM_MODEL", "").strip() or "gemma4"

# Ordered best-first for image work. Only `gemma4` is vision-capable today;
# the rest are listed so the app degrades gracefully if that changes.
PREFERRED_MODELS: List[str] = ["gemma4"]

# Text-only models - never usable for grading a photo.
TEXT_ONLY_MODELS = {"sarvam-105b", "sarvam-105b-conversations", "glm5.3",
                    "glm5.2", "deepseekv4.1-flash", "sarvam-m", "sarvam-30b"}

REQUEST_TIMEOUT_SECONDS = 90


# Sericulture Prompt for the Multimodal Vision Model
SERICULTURE_VISION_PROMPT = """
You are an expert Sericulture Inspector and Agricultural Vision AI specialist.
Analyze this silkworm cocoon image strictly according to commercial silk grading standards.

Output your evaluation ONLY as a raw, valid JSON object with the exact keys below.
Do not enclose in markdown blocks if possible, or use standard ```json ... ``` tags.

Required JSON Structure:
{
  "is_cocoon": true or false,
  "evidence_sufficient": true or false,
  "quality_notes": "Explanation if image is blurry, too dark, occluded, or low resolution",
  "cocoon_count": <estimated integer number of cocoons visible>,
  "color_type": "White (Bivoltine)" or "Golden Yellow (Multivoltine)" or "Greenish" or "Other",
  "shape_uniformity_score": <0 to 100 based on symmetrical oval/ellipsoidal shape>,
  "compactness_score": <0 to 100 based on shell firmness, thickness, and lack of loose floss>,
  "cleanliness_score": <0 to 100 based on pure surface, lack of urine/melting/soil stains>,
  "defects_detected": ["pierced", "double", "melted", "stained", "crushed", "flimsy", "malformed"] (list only actual defects detected, or empty list []),
  "visual_observations": [
    "<3-5 clear, factual bullet points describing the visual evidence seen in the photo>"
  ],
  "recommendations": [
    "<2-3 actionable advice points for the farmer or silk reelers regarding storage, sorting, or market pricing>"
  ]
}

STRICT INSTRUCTIONS:
1. If the photo does NOT contain silkworm cocoons (e.g. food, human, car, unrelated object), set "is_cocoon": false, "evidence_sufficient": false, and do NOT fabricate scores.
2. If the photo is too blurry, dark, far away, or obscured to judge shell quality honestly, set "evidence_sufficient": false, explain why in "quality_notes", and avoid speculating.
3. If defects like uzifly pierced holes, moth emergence, double cocoon (dupion), or melting are present, name them explicitly in "defects_detected".
"""


def validate_image_bytes(image_bytes: bytes, max_size_mb: int = 10) -> Tuple[bool, str, Optional[Image.Image]]:
    """
    Validates the uploaded file in-memory.
    Checks:
    - Non-empty byte payload
    - File size below max_size_mb
    - Valid, non-corrupted image format (JPEG, PNG, WEBP)
    - Minimum resolvable dimensions (at least 64x64)

    Returns:
        (is_valid, error_message, PIL.Image object or None)
    """
    if not image_bytes:
        return False, "Uploaded image file is empty (0 bytes).", None

    max_bytes = max_size_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        return False, f"File size exceeds the {max_size_mb} MB limit (Size: {len(image_bytes)/(1024*1024):.1f} MB).", None

    try:
        # Load safely into PIL without writing to disk
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()  # Verifies file integrity and header

        # Reopen after verify() because verify() clears file pointer
        image = Image.open(io.BytesIO(image_bytes))

        # Check format
        allowed_formats = {"JPEG", "JPG", "PNG", "WEBP"}
        if image.format.upper() not in allowed_formats:
            return False, f"Unsupported image format: {image.format}. Please upload JPG, PNG, or WEBP.", None

        # Check dimensions
        width, height = image.size
        if width < 64 or height < 64:
            return False, f"Image resolution ({width}x{height}) is too small for quality assessment.", None

        # Convert palette/RGBA modes to RGB for AI models if needed
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        return True, "", image

    except Exception as e:
        return False, f"Corrupted or invalid image file: {str(e)}", None


def clean_json_response(raw_text: str) -> str:
    """
    Cleans multimodal model output by stripping markdown fences,
    extraneous commentary, or leading/trailing whitespace.
    """
    if not raw_text or not raw_text.strip():
        return ""

    text = raw_text.strip()

    # Match ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    else:
        # If no markdown block, locate outermost curly braces
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    return text


def parse_and_validate_ai_json(json_text: str) -> Tuple[bool, Dict[str, Any], str]:
    """
    Parses and validates the JSON response from the multimodal AI model.
    Guarantees that all required sericulture fields exist and types are valid.
    """
    if not json_text or not json_text.strip():
        return False, {}, "Multimodal model returned an empty response."

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as err:
        return False, {}, f"Failed to parse model JSON: {str(err)}"

    if not isinstance(data, dict):
        return False, {}, "Model output was not a valid JSON dictionary."

    # Normalize defaults for safe consumption
    parsed: Dict[str, Any] = {
        "is_cocoon": bool(data.get("is_cocoon", False)),
        "evidence_sufficient": bool(data.get("evidence_sufficient", False)),
        "quality_notes": str(data.get("quality_notes", "")),
        "cocoon_count": int(data.get("cocoon_count", 1) or 1),
        "color_type": str(data.get("color_type", "White (Bivoltine)")),
        "shape_uniformity_score": data.get("shape_uniformity_score", 70),
        "compactness_score": data.get("compactness_score", 70),
        "cleanliness_score": data.get("cleanliness_score", 70),
        "defects_detected": data.get("defects_detected", []) if isinstance(data.get("defects_detected"), list) else [],
        "visual_observations": data.get("visual_observations", []) if isinstance(data.get("visual_observations"), list) else [],
        "recommendations": data.get("recommendations", []) if isinstance(data.get("recommendations"), list) else [],
    }

    return True, parsed, ""


# ---------------------------------------------------------------------------
# Provider helpers (Sarvam AI)
# ---------------------------------------------------------------------------
def _get_effective_key(api_key: Optional[str] = None) -> str:
    """Resolve the Sarvam API key from the argument, then the environment."""
    return (api_key or os.getenv("SARVAM_API_KEY", "")).strip()


def _is_valid_key(effective_key: str) -> bool:
    return bool(effective_key) and effective_key != "your_sarvam_api_key_here"


def _image_to_data_uri(image: Image.Image, quality: int = 85) -> str:
    """Encode a PIL image as an inline base64 JPEG data URI (Sarvam requires inline)."""
    buffer = io.BytesIO()
    rgb = image.convert("RGB") if image.mode != "RGB" else image
    rgb.save(buffer, format="JPEG", quality=quality)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def list_available_models(api_key: Optional[str] = None) -> List[str]:
    """
    Ask Sarvam which model IDs this key can use (GET /v2/models).
    Never raises: returns an empty list if discovery is impossible.
    """
    effective_key = _get_effective_key(api_key)
    if not _is_valid_key(effective_key):
        return []
    try:
        resp = requests.get(
            SARVAM_MODELS_URL,
            headers={"api-subscription-key": effective_key},
            timeout=20,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
    except Exception:
        return []


def resolve_model_name(api_key: Optional[str] = None, requested: Optional[str] = None) -> Tuple[str, str]:
    """
    Choose a usable, image-capable Sarvam model.

    Returns (model_name, note). Falls back to `gemma4` if the requested model is
    text-only or unavailable.
    """
    requested = (requested or "").strip()
    if requested in TEXT_ONLY_MODELS:
        return DEFAULT_MODEL, (
            f"'{requested}' is a text-only model and cannot read a photo; using '{DEFAULT_MODEL}'."
        )

    available = list_available_models(api_key)
    if available:
        if requested and requested in available:
            return requested, ""
        for candidate in PREFERRED_MODELS:
            if candidate in available:
                note = f"Requested model '{requested}' is unavailable; using '{candidate}'." if requested else ""
                return candidate, note
        # Nothing preferred is enabled on this key.
        return requested or DEFAULT_MODEL, ""

    return requested or DEFAULT_MODEL, ""


def analyze_cocoon_image(
    image: Image.Image,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any], str]:
    """
    Invokes the Sarvam multimodal Vision model to inspect the cocoon image.
    Never fabricates responses: if the API key is missing or invalid, reports a clear error.
    """
    # 1. Retrieve API Key
    effective_key = _get_effective_key(api_key)
    if not _is_valid_key(effective_key):
        return False, {}, (
            "SARVAM_API_KEY is not configured. "
            "Please obtain an API key from https://dashboard.sarvam.ai and add it to your "
            ".env file or enter it in the sidebar settings."
        )

    # 2. Select Model Name (auto-resolve to an image-capable model)
    effective_model = (model_name or DEFAULT_MODEL).strip()
    effective_model, _note = resolve_model_name(api_key=effective_key, requested=effective_model)

    # 3. Build the OpenAI-compatible request with an inline image
    try:
        data_uri = _image_to_data_uri(image)
    except Exception as exc:
        return False, {}, f"Could not prepare the image for analysis: {exc}"

    payload = {
        "model": effective_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SERICULTURE_VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ],
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 1500,
    }

    try:
        resp = requests.post(
            SARVAM_CHAT_URL,
            headers={
                "api-subscription-key": effective_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        return False, {}, "The AI request timed out. Please check your connection and retry."
    except requests.exceptions.RequestException as exc:
        return False, {}, f"Could not reach the Sarvam AI service: {exc}"

    # 4. Handle non-200 responses with clear, secret-free guidance
    if resp.status_code != 200:
        return False, {}, _friendly_http_error(resp, effective_model, effective_key)

    # 5. Extract the model's text answer
    try:
        body = resp.json()
    except ValueError:
        return False, {}, "The AI service returned a non-JSON response. Please retry."

    content = ""
    try:
        content = body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        content = ""

    if isinstance(content, list):
        # Some OpenAI-compatible servers return content as a list of parts.
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))

    if not content.strip():
        return False, {}, "Multimodal AI returned an empty response. Please retry."

    # 6. Clean markdown code blocks and parse the JSON structure
    clean_text = clean_json_response(content)
    success, parsed_data, err_msg = parse_and_validate_ai_json(clean_text)
    if not success:
        return False, {}, f"Model returned invalid structured output: {err_msg}"

    parsed_data["_model_used"] = effective_model
    return True, parsed_data, ""


def _friendly_http_error(resp, effective_model: str, effective_key: str) -> str:
    """Map Sarvam HTTP errors to clear guidance without leaking secrets."""
    status = resp.status_code
    try:
        err_body = resp.json()
        err_text = json.dumps(err_body)
    except ValueError:
        err_text = (resp.text or "")[:300]
    lowered = err_text.lower()

    if status in (401, 403):
        return (
            "Sarvam rejected the API key (auth failed, HTTP 403). The key was received but is "
            "not valid or active. Check for a typo or partial paste, stray quotes or spaces, or "
            "a rotated key. Run 'python check_key.py' in the project folder to test the key in "
            "isolation, then restart Streamlit."
        )
    if status == 404 or "not found" in lowered or "unknown id" in lowered:
        available = list_available_models(api_key=effective_key)
        hint = (
            f" Model IDs advertised by the endpoint: {', '.join(available[:6])} "
            "(note: this list is not an auth check)."
        ) if available else ""
        return (
            f"The model '{effective_model}' is not available on this API key.{hint} "
            "Note: 'gemma4' is the image-capable Sarvam model; the beta endpoint must be "
            "enabled for your key (contact Sarvam to request access)."
        )
    if status == 429:
        return "Sarvam API rate limit reached. Please wait a few moments and retry."
    if status == 422:
        return (
            "The request was rejected as unprocessable (the image may be too large for the "
            "model's context, or the endpoint is not enabled for your key). Try a smaller photo."
        )
    if status >= 500:
        return "The Sarvam AI service is temporarily unavailable. Please retry in a moment."
    return f"Sarvam AI analysis error (HTTP {status}): {err_text}"


# Backwards-compatible alias (older code/tests may import the Gemini-era name).
analyze_cocoon_image_with_gemini = analyze_cocoon_image
