"""
SilkCocoonAI - Transparent Market Price Estimation (market.py)

Turns an audited cocoon grade into an indicative farm-gate / mandi price in INR.

IMPORTANT / DISCLAIMER
----------------------
The rates below are INDICATIVE BENCHMARK VALUES compiled for demonstration and
hackathon purposes only. Real cocoon prices in Indian mandis (e.g. Ramanagara,
Siddlaghatta, Kolar, Dharmapuri, Anantapur) move daily with the season, moisture
content, race (bivoltine vs multivoltine/crossbreed), and local demand. Always
confirm against the day's official Sericulture Department / market rate before
making a commercial decision. This tool is not a substitute for a licensed buyer
or the local cocoon market price bulletin.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Indicative price bands (INR per kg of fresh cocoons)
# ---------------------------------------------------------------------------
BASE_PRICE_PER_KG: Dict[str, float] = {
    "Grade A": 640.0,   # Clean, firm, uniform - premium automatic reeling
    "Grade B": 520.0,   # Standard commercial reeling
    "Grade C": 390.0,   # Coarse yarn / local reeling
    "Reject": 170.0,    # Spun silk waste / handloom value only
    "Manual Review": 0.0,
}

# Race / colour adjustment. Bivoltine white silk generally commands a premium;
# multivoltine and off-colour lots trade at a discount.
COLOR_MULTIPLIERS: Dict[str, float] = {
    "White (Bivoltine)": 1.10,
    "Golden Yellow (Multivoltine)": 0.92,
    "Greenish": 0.85,
    "Other": 0.80,
    "Unknown": 1.00,
}

# Grades/states that must never be priced or counted as a lot line.
NON_GRADABLE_GRADES = {"", "manual review", "error", "n/a", "unknown", "none"}

# Above this moisture percentage a drying/weight-risk discount is applied.
ALLOWED_MOISTURE_PCT = 12.0
MOISTURE_DISCOUNT_PER_PCT = 0.01  # 1% price reduction per extra % moisture


def grade_rate_per_kg(
    grade: str,
    color_type: str = "Unknown",
    base_rates: Optional[Dict[str, float]] = None,
    rate_override: Optional[float] = None,
) -> float:
    """
    Return the indicative rate (INR/kg) for a grade + colour combination.

    `rate_override` lets a user pin the exact local mandi rate for the grade,
    bypassing the built-in benchmark.
    """
    if rate_override is not None and rate_override > 0:
        return round(float(rate_override), 2)
    base = (base_rates or BASE_PRICE_PER_KG).get(grade, 0.0)
    multiplier = COLOR_MULTIPLIERS.get(color_type, 1.0)
    return round(base * multiplier, 2)


@dataclass
class LotLine:
    """One grade line inside a lot price estimate."""
    grade: str
    color_type: str
    weight_kg: float
    rate_per_kg: float
    value: float


@dataclass
class PriceEstimate:
    """Full price breakdown for a lot of cocoons."""
    total_weight_kg: float
    total_value: float
    average_rate_per_kg: float
    moisture_pct: float
    moisture_discount_pct: float
    lines: List[Dict[str, Any]] = field(default_factory=list)
    currency: str = "INR"
    disclaimer: str = (
        "Indicative benchmark only. Verify against your local mandi / Sericulture "
        "Department daily rate before trading."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _moisture_discount(moisture_pct: float) -> float:
    """Fraction (0-0.5) of price removed for excessive moisture."""
    if moisture_pct is None or moisture_pct <= ALLOWED_MOISTURE_PCT:
        return 0.0
    extra = moisture_pct - ALLOWED_MOISTURE_PCT
    return min(0.5, extra * MOISTURE_DISCOUNT_PER_PCT)


def estimate_lot_value(
    items: List[Dict[str, Any]],
    base_rates: Optional[Dict[str, float]] = None,
    rate_override: Optional[float] = None,
    moisture_pct: float = 0.0,
) -> PriceEstimate:
    """
    Estimate the value of a lot.

    `items` is a list of dicts, each: {"grade": str, "color_type": str, "weight_kg": float}.
    Rows with grade "Manual Review" or a non-positive weight are skipped (value 0).
    """
    lines: List[LotLine] = []
    total_weight = 0.0
    total_value = 0.0
    discount = _moisture_discount(moisture_pct)

    for item in items or []:
        grade = str(item.get("grade", "")).strip()
        color = str(item.get("color_type", "Unknown")).strip() or "Unknown"
        try:
            weight = float(item.get("weight_kg", 0) or 0)
        except (TypeError, ValueError):
            weight = 0.0

        # Skip non-gradable lines (manual review, errors, blank grades) so their
        # weight is never counted toward the lot total.
        if weight <= 0 or grade.strip().lower() in NON_GRADABLE_GRADES:
            continue

        rate = grade_rate_per_kg(grade, color, base_rates=base_rates, rate_override=rate_override)
        # An unknown grade with no benchmark and no override has no price: skip it
        # rather than counting its weight at zero value.
        if rate <= 0 and rate_override is None:
            continue
        value = rate * weight * (1 - discount)

        lines.append(LotLine(
            grade=grade,
            color_type=color,
            weight_kg=round(weight, 3),
            rate_per_kg=rate,
            value=round(value, 2),
        ))
        total_weight += weight
        total_value += value

    average_rate = round(total_value / total_weight, 2) if total_weight > 0 else 0.0

    return PriceEstimate(
        total_weight_kg=round(total_weight, 3),
        total_value=round(total_value, 2),
        average_rate_per_kg=average_rate,
        moisture_pct=round(float(moisture_pct or 0), 2),
        moisture_discount_pct=round(discount * 100, 2),
        lines=[asdict(line) for line in lines],
    )


def estimate_single_grade(
    grade: str,
    color_type: str = "Unknown",
    weight_kg: float = 1.0,
    base_rates: Optional[Dict[str, float]] = None,
    rate_override: Optional[float] = None,
) -> PriceEstimate:
    """Convenience wrapper for pricing a single grade/colour at a given weight."""
    return estimate_lot_value(
        [{"grade": grade, "color_type": color_type, "weight_kg": weight_kg}],
        base_rates=base_rates,
        rate_override=rate_override,
    )
