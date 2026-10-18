"""
Unit tests for Image Validation & Safety Guardrails (tests/test_image_validation.py)
"""

import io
import pytest
from PIL import Image
from image_analysis import validate_image_bytes


def create_dummy_image(format="JPEG", size=(200, 200), color=(255, 255, 255)) -> bytes:
    """Helper to generate in-memory dummy image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


def test_valid_jpeg_upload():
    """Verify that a standard JPEG upload is accepted."""
    img_bytes = create_dummy_image("JPEG", size=(300, 300))
    is_valid, err_msg, img_obj = validate_image_bytes(img_bytes)

    assert is_valid is True
    assert err_msg == ""
    assert img_obj is not None
    assert img_obj.size == (300, 300)


def test_valid_png_upload():
    """Verify that a valid PNG upload is accepted."""
    img_bytes = create_dummy_image("PNG", size=(150, 150))
    is_valid, err_msg, img_obj = validate_image_bytes(img_bytes)

    assert is_valid is True
    assert img_obj is not None


def test_empty_image_upload():
    """Verify that an empty byte array (0 bytes) is rejected with clear error."""
    is_valid, err_msg, img_obj = validate_image_bytes(b"")

    assert is_valid is False
    assert "empty" in err_msg.lower()
    assert img_obj is None


def test_oversized_image_upload():
    """Verify that images exceeding the max size limit are rejected."""
    # 2MB dummy payload with 1MB limit for testing
    huge_bytes = b"0" * (2 * 1024 * 1024)
    is_valid, err_msg, img_obj = validate_image_bytes(huge_bytes, max_size_mb=1)

    assert is_valid is False
    assert "exceeds" in err_msg.lower()
    assert img_obj is None


def test_corrupted_image_bytes():
    """Verify that malformed/corrupted byte streams fail gracefully without crashing."""
    corrupted_bytes = b"GIF89aNOT_A_VALID_IMAGE_STREAM_RANDOM_CORRUPTION_123456789"
    is_valid, err_msg, img_obj = validate_image_bytes(corrupted_bytes)

    assert is_valid is False
    assert "corrupted" in err_msg.lower() or "invalid" in err_msg.lower()
    assert img_obj is None


def test_undersized_image_resolution():
    """Verify that thumbnail/undersized images (<64x64) are flagged for manual review."""
    tiny_bytes = create_dummy_image("JPEG", size=(32, 32))
    is_valid, err_msg, img_obj = validate_image_bytes(tiny_bytes)

    assert is_valid is False
    assert "too small" in err_msg.lower()
    assert img_obj is None
