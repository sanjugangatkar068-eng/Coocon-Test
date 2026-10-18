"""
Unit tests for the market price estimator (tests/test_market.py).
"""

import pytest
from market import (
    estimate_lot_value,
    estimate_single_grade,
    grade_rate_per_kg,
    BASE_PRICE_PER_KG,
    COLOR_MULTIPLIERS,
)


def test_grade_a_rate_includes_bivoltine_premium():
    rate = grade_rate_per_kg("Grade A", "White (Bivoltine)")
    expected = round(BASE_PRICE_PER_KG["Grade A"] * COLOR_MULTIPLIERS["White (Bivoltine)"], 2)
    assert rate == expected


def test_single_grade_value():
    est = estimate_single_grade("Grade A", "White (Bivoltine)", weight_kg=10)
    assert est.total_weight_kg == 10
    assert est.total_value > 0
    assert est.average_rate_per_kg == grade_rate_per_kg("Grade A", "White (Bivoltine)")


def test_rate_override_wins_over_benchmark():
    est = estimate_single_grade("Grade C", "Other", weight_kg=5, rate_override=400)
    assert est.average_rate_per_kg == 400.0
    assert est.total_value == 2000.0


def test_manual_review_and_zero_weight_are_skipped():
    est = estimate_lot_value([
        {"grade": "Manual Review", "color_type": "Unknown", "weight_kg": 3},
        {"grade": "Grade B", "color_type": "Unknown", "weight_kg": 0},
    ])
    assert est.total_weight_kg == 0
    assert est.total_value == 0
    assert est.lines == []


def test_moisture_discount_reduces_value():
    dry = estimate_single_grade("Grade A", "White (Bivoltine)", weight_kg=10)
    wet = estimate_lot_value(
        [{"grade": "Grade A", "color_type": "White (Bivoltine)", "weight_kg": 10}],
        moisture_pct=20,
    )
    assert wet.total_value < dry.total_value
    assert wet.moisture_discount_pct > 0


def test_lot_multi_grade_totals():
    est = estimate_lot_value([
        {"grade": "Grade A", "color_type": "White (Bivoltine)", "weight_kg": 10},
        {"grade": "Grade B", "color_type": "White (Bivoltine)", "weight_kg": 20},
    ])
    assert est.total_weight_kg == 30
    assert len(est.lines) == 2
    assert est.total_value == round(
        grade_rate_per_kg("Grade A", "White (Bivoltine)") * 10
        + grade_rate_per_kg("Grade B", "White (Bivoltine)") * 20,
        2,
    )


def test_error_and_unknown_grades_do_not_inflate_lot_weight():
    """Non-gradable / unpriced lines must not count toward weight or skew the rate."""
    est = estimate_lot_value([
        {"grade": "Grade A", "color_type": "White (Bivoltine)", "weight_kg": 2.0},
        {"grade": "Error", "color_type": "Unknown", "weight_kg": 5.0},
        {"grade": "Manual Review", "color_type": "Unknown", "weight_kg": 3.0},
        {"grade": "Bogus", "color_type": "Unknown", "weight_kg": 4.0},
    ])
    assert est.total_weight_kg == 2.0
    assert est.average_rate_per_kg == grade_rate_per_kg("Grade A", "White (Bivoltine)")
