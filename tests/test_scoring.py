"""
Unit tests for Transparent Scoring & Manual-Review Logic (tests/test_scoring.py)
"""

import pytest
from scoring import calculate_cocoon_grade, CocoonGradingResult


def test_grade_a_sufficient_evidence():
    """Verify that a pristine cocoon receives Grade A without defect penalties."""
    ai_data = {
        "is_cocoon": True,
        "evidence_sufficient": True,
        "shape_uniformity_score": 92,
        "compactness_score": 95,
        "cleanliness_score": 94,
        "defects_detected": [],
        "color_type": "White (Bivoltine)",
        "cocoon_count": 1,
        "visual_observations": ["Well-formed oval cocoon", "High shell tightness"],
        "recommendations": ["Store in dry, ventilated space"],
    }

    result = calculate_cocoon_grade(ai_data)

    assert result.status == "SUCCESS"
    assert result.is_cocoon is True
    assert result.evidence_sufficient is True
    assert result.grade == "Grade A"
    assert result.overall_score is not None
    assert result.overall_score >= 85.0
    assert result.defect_penalty == 0.0
    assert ">80%" in result.estimated_reelability


def test_grade_b_standard_cocoon():
    """Verify Grade B evaluation with minor surface variations."""
    ai_data = {
        "is_cocoon": True,
        "evidence_sufficient": True,
        "shape_uniformity_score": 78,
        "compactness_score": 75,
        "cleanliness_score": 76,
        "defects_detected": [],
        "color_type": "White (Bivoltine)",
        "cocoon_count": 1,
    }

    result = calculate_cocoon_grade(ai_data)

    assert result.status == "SUCCESS"
    assert result.grade == "Grade B"
    assert 70.0 <= result.overall_score < 85.0


def test_fatal_defect_pierced_cocoon():
    """Verify that pierced cocoon (uzifly parasite) is immediately rejected regardless of sub-scores."""
    ai_data = {
        "is_cocoon": True,
        "evidence_sufficient": True,
        "shape_uniformity_score": 90,
        "compactness_score": 90,
        "cleanliness_score": 90,
        "defects_detected": ["pierced"],  # Fatal uzifly defect
    }

    result = calculate_cocoon_grade(ai_data)

    assert result.status == "SUCCESS"
    assert result.grade == "Reject"
    assert result.overall_score <= 35.0  # Capped at Reject
    assert result.defect_severity == "severe"
    assert "Reject from Reeling" in result.commercial_action


def test_fatal_defect_melted_cocoon():
    """Verify that melted (diseased pupa) cocoon is rejected."""
    ai_data = {
        "is_cocoon": True,
        "evidence_sufficient": True,
        "shape_uniformity_score": 85,
        "compactness_score": 85,
        "cleanliness_score": 80,
        "defects_detected": ["melted"],
    }

    result = calculate_cocoon_grade(ai_data)

    assert result.grade == "Reject"
    assert result.overall_score <= 35.0


def test_major_defect_double_cocoon():
    """Verify double cocoon (dupion) applies appropriate penalty and action."""
    ai_data = {
        "is_cocoon": True,
        "evidence_sufficient": True,
        "shape_uniformity_score": 80,
        "compactness_score": 80,
        "cleanliness_score": 80,
        "defects_detected": ["double"],
    }

    result = calculate_cocoon_grade(ai_data)

    assert result.defect_penalty >= 30.0
    assert result.overall_score <= 55.0


def test_no_score_generated_when_not_a_cocoon():
    """
    CRITICAL GUARDRAIL: When an image is not a cocoon, no fabricated score must be produced.
    Must route to MANUAL_REVIEW_REQUIRED.
    """
    ai_data = {
        "is_cocoon": False,
        "evidence_sufficient": False,
        "visual_observations": ["Detected object is a ceramic cup, not a silkworm cocoon."],
    }

    result = calculate_cocoon_grade(ai_data)

    assert result.status == "MANUAL_REVIEW_REQUIRED"
    assert result.is_cocoon is False
    assert result.overall_score is None  # Never fabricate score
    assert result.grade == "Manual Review"
    assert "does not appear to contain" in result.manual_review_reason


def test_no_score_generated_when_evidence_insufficient():
    """
    CRITICAL GUARDRAIL: When evidence is insufficient (blurry, dark), do not speculate.
    Must provide helpful manual review guidance.
    """
    ai_data = {
        "is_cocoon": True,
        "evidence_sufficient": False,
        "quality_notes": "Camera blur and low lighting prevent shell texture inspection.",
    }

    result = calculate_cocoon_grade(ai_data)

    assert result.status == "MANUAL_REVIEW_REQUIRED"
    assert result.is_cocoon is True
    assert result.evidence_sufficient is False
    assert result.overall_score is None
    assert result.grade == "Manual Review"
    assert len(result.guidance_tips) > 0
    assert "blur" in result.manual_review_reason.lower()
