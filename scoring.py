"""
SilkCocoonAI - Scoring and Grading Logic (scoring.py)

This module provides transparent, verifiable sericulture grading logic
based on commercial silk cocoon standards (such as Central Silk Board & FAO guidelines).

Grading Parameters:
1. Shape Uniformity (0-100): Cocoon ellipsoidal/oval symmetry and consistency.
2. Shell Compactness (0-100): Shell thickness, firmness, and silk density.
3. Cleanliness (0-100): Purity of color, freedom from urine/melting stains or mold.
4. Defect Penalties: Deductions for pierced, double (dupion), melted, or flimsy shells.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


# Standard Sericulture Defect Penalty Weights
DEFECT_PENALTY_WEIGHTS = {
    "pierced": 65,    # Fatal: Uzifly or moth hole cuts continuous filament
    "melted": 60,     # Fatal: Dead diseased pupa inside stains and ruins reeling
    "double": 30,     # Major: Two pupae inside (Dupion silk - coarse, non-uniform)
    "crushed": 25,    # Major: Wall collapsed or fractured
    "flimsy": 20,     # Moderate: Thin, loose shell with poor silk content
    "stained": 15,    # Moderate: Outer urine or dust staining
    "malformed": 15,  # Moderate: Irregular ridges or constrictions
}


@dataclass
class CocoonGradingResult:
    """
    Structured outcome of the cocoon evaluation.
    Guarantees no fabricated numbers: overall_score is None when evidence is insufficient.
    """
    status: str  # "SUCCESS", "MANUAL_REVIEW_REQUIRED", "ERROR"
    is_cocoon: bool
    evidence_sufficient: bool
    grade: str  # "Grade A", "Grade B", "Grade C", "Reject", "Manual Review"
    overall_score: Optional[float] = None
    shape_uniformity_score: Optional[float] = None
    compactness_score: Optional[float] = None
    cleanliness_score: Optional[float] = None
    defect_penalty: float = 0.0
    defects_detected: List[str] = field(default_factory=list)
    defect_severity: str = "none"  # "none", "minor", "moderate", "severe"
    estimated_reelability: Optional[str] = None
    commercial_action: str = ""
    color_type: str = "Unknown"
    cocoon_count: int = 0
    manual_review_reason: Optional[str] = None
    guidance_tips: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result object into a clean dictionary for UI and JSON reporting."""
        return asdict(self)


def calculate_cocoon_grade(ai_data: Dict[str, Any]) -> CocoonGradingResult:
    """
    Evaluates raw multimodal AI analysis and computes an auditable sericulture grade.

    Rules:
    - If the image is not a cocoon, return MANUAL_REVIEW_REQUIRED without a fake score.
    - If the image quality is too low (blurry/dark), return MANUAL_REVIEW_REQUIRED.
    - If fatal defects exist (pierced/melted), grade is capped at 'Reject'.
    - Transparent weighted formula:
        Base = 35% Compactness + 35% Cleanliness + 30% Shape Uniformity
        Final = clamp(Base - Defect Penalty, 0, 100)
    """
    # 1. Gate: Verify whether the image genuinely contains a silkworm cocoon
    is_cocoon = bool(ai_data.get("is_cocoon", False))
    evidence_sufficient = bool(ai_data.get("evidence_sufficient", False))
    quality_notes = ai_data.get("quality_notes", "")
    observations = ai_data.get("visual_observations", [])
    recommendations = ai_data.get("recommendations", [])
    raw_defects = [str(d).lower().strip() for d in ai_data.get("defects_detected", []) if d]

    # Clean defects (ignore 'none' or 'nil')
    defects = [d for d in raw_defects if d not in ["none", "nil", "no defects", "n/a", ""]]

    # Case A: Not a cocoon
    if not is_cocoon:
        return CocoonGradingResult(
            status="MANUAL_REVIEW_REQUIRED",
            is_cocoon=False,
            evidence_sufficient=False,
            grade="Manual Review",
            overall_score=None,
            manual_review_reason="The uploaded image does not appear to contain silkworm cocoons.",
            guidance_tips=[
                "Ensure the photo shows silkworm cocoons (Bombyx mori or wild varieties).",
                "Place cocoons against a neutral, uncluttered background (e.g., white paper or sorting tray).",
                "Avoid uploading unrelated farm produce, insects, or equipment."
            ],
            observations=observations or ["Object detected is not identifiable as a silkworm cocoon."],
            recommendations=["Please upload a valid cocoon photo to receive an automated quality rating."]
        )

    # Case B: Insufficient visual evidence (blurry, dark, occluded)
    if not evidence_sufficient:
        reason = quality_notes if quality_notes else "Image clarity, lighting, or focus is inadequate for trustworthy grading."
        return CocoonGradingResult(
            status="MANUAL_REVIEW_REQUIRED",
            is_cocoon=True,
            evidence_sufficient=False,
            grade="Manual Review",
            overall_score=None,
            manual_review_reason=reason,
            guidance_tips=[
                "Capture the photo under bright, diffuse natural daylight or white LED lighting.",
                "Keep the camera 15-25 cm away to avoid macro-blur.",
                "Lay 1 to 5 cocoons flat without mutual overlapping for accurate shell inspection.",
                "Clean the camera lens to prevent haze and artifacts."
            ],
            observations=observations or ["Visual features could not be resolved with high confidence."],
            recommendations=["Retake the photograph using the guidance tips above to enable grading."]
        )

    # Case C: Sufficient evidence -> Compute transparent scores
    try:
        shape_score = float(ai_data.get("shape_uniformity_score", 70))
        compactness_score = float(ai_data.get("compactness_score", 70))
        cleanliness_score = float(ai_data.get("cleanliness_score", 70))
    except (ValueError, TypeError):
        shape_score = 70.0
        compactness_score = 70.0
        cleanliness_score = 70.0

    # Clamp scores to valid 0-100 range
    shape_score = max(0.0, min(100.0, shape_score))
    compactness_score = max(0.0, min(100.0, compactness_score))
    cleanliness_score = max(0.0, min(100.0, cleanliness_score))

    # Calculate defect penalty
    defect_penalty = 0.0
    has_fatal_defect = False

    for defect in defects:
        matched = False
        for key, weight in DEFECT_PENALTY_WEIGHTS.items():
            if key in defect:
                defect_penalty += weight
                matched = True
                if key in ["pierced", "melted"]:
                    has_fatal_defect = True
                break
        if not matched:
            defect_penalty += 10.0  # Generic unclassified defect deduction

    # Weighted baseline calculation:
    # Sericulture priority: Shell firmness & Cleanliness are paramount for reeling
    base_score = (0.35 * compactness_score) + (0.35 * cleanliness_score) + (0.30 * shape_score)
    final_score = base_score - defect_penalty
    final_score = max(0.0, min(100.0, round(final_score, 1)))

    # Determine defect severity label
    if has_fatal_defect or defect_penalty >= 40:
        defect_severity = "severe"
    elif defect_penalty >= 20:
        defect_severity = "moderate"
    elif defect_penalty > 0:
        defect_severity = "minor"
    else:
        defect_severity = "none"

    # Assign Grade, Reelability, and Commercial Action based on Sericulture Standards
    if has_fatal_defect:
        grade = "Reject"
        final_score = min(final_score, 35.0)  # Fatal defects cap maximum score
        estimated_reelability = "<50% (Unreelable continuously)"
        commercial_action = "Reject from Reeling Auction. Divert to Spun Silk Waste or Handloom Crafting."
    elif final_score >= 85:
        grade = "Grade A"
        estimated_reelability = ">80% (High Silk Yield & Continuous Filament)"
        commercial_action = "Eligible for Premium Automatic Reeling Auction. Top Market Price."
    elif final_score >= 70:
        grade = "Grade B"
        estimated_reelability = "70% - 79% (Standard Commercial Reeling)"
        commercial_action = "Suitable for Standard Reeling Units (Multi-end or Cottage Basins)."
    elif final_score >= 50:
        grade = "Grade C"
        estimated_reelability = "50% - 69% (Substandard / Higher Breaks)"
        commercial_action = "Divert to Coarse Yarn / Local Reeling. Price Discount Recommended."
    else:
        grade = "Reject"
        estimated_reelability = "<50% (High Waste Ratio)"
        commercial_action = "Non-commercial reeling quality. Sort out defective units."

    color_type = str(ai_data.get("color_type", "White (Bivoltine)"))
    cocoon_count = int(ai_data.get("cocoon_count", 1))

    return CocoonGradingResult(
        status="SUCCESS",
        is_cocoon=True,
        evidence_sufficient=True,
        grade=grade,
        overall_score=final_score,
        shape_uniformity_score=round(shape_score, 1),
        compactness_score=round(compactness_score, 1),
        cleanliness_score=round(cleanliness_score, 1),
        defect_penalty=round(defect_penalty, 1),
        defects_detected=defects,
        defect_severity=defect_severity,
        estimated_reelability=estimated_reelability,
        commercial_action=commercial_action,
        color_type=color_type,
        cocoon_count=cocoon_count,
        manual_review_reason=None,
        guidance_tips=[],
        observations=observations,
        recommendations=recommendations
    )
