"""
Unit tests for batch lot aggregation (tests/test_batch.py).
"""

import pytest
from batch import build_batch_report, batch_report_to_csv


def _res(grade, score, status="SUCCESS", defects=None, color="White (Bivoltine)"):
    return {
        "name": f"{grade}.jpg",
        "result": {
            "grade": grade,
            "overall_score": score,
            "status": status,
            "defects_detected": defects or [],
            "color_type": color,
        },
        "weight_kg": 1.0,
    }


def test_aggregate_counts_and_average():
    rep = build_batch_report([_res("Grade A", 90), _res("Grade B", 75), _res("Grade A", 88)])
    assert rep.total_images == 3
    assert rep.graded_count == 3
    assert rep.grade_counts["Grade A"] == 2
    assert rep.dominant_grade == "Grade A"
    assert rep.worst_grade == "Grade B"
    assert rep.average_score == round((90 + 75 + 88) / 3, 1)


def test_manual_review_is_not_scored():
    rep = build_batch_report([
        {
            "name": "blurry.jpg",
            "result": {
                "grade": "Manual Review",
                "overall_score": None,
                "status": "MANUAL_REVIEW_REQUIRED",
                "defects_detected": [],
                "color_type": "Unknown",
            },
            "weight_kg": 1.0,
        },
        _res("Grade A", 90),
    ])
    assert rep.manual_review_count == 1
    assert rep.graded_count == 1
    assert rep.average_score == 90.0


def test_error_entries_are_counted_not_scored():
    rep = build_batch_report([{"name": "bad.jpg", "result": {}, "weight_kg": 1.0, "error": "Corrupted image"}])
    assert rep.error_count == 1
    assert rep.graded_count == 0
    assert rep.lot_recommendation  # non-empty guidance


def test_defect_frequency():
    rep = build_batch_report([
        _res("Reject", 20, defects=["pierced"]),
        _res("Reject", 25, defects=["pierced", "melted"]),
    ])
    assert rep.defect_frequency["pierced"] == 2
    assert rep.defect_frequency["melted"] == 1


def test_weighted_average_uses_weights():
    rep = build_batch_report([
        {"name": "a", "result": {"grade": "Grade A", "overall_score": 100, "status": "SUCCESS",
                                 "defects_detected": [], "color_type": "Unknown"}, "weight_kg": 1.0},
        {"name": "b", "result": {"grade": "Grade C", "overall_score": 0, "status": "SUCCESS",
                                 "defects_detected": [], "color_type": "Unknown"}, "weight_kg": 9.0},
    ])
    assert rep.weighted_average_score == 10.0


def test_csv_export_contains_rows_and_summary():
    rep = build_batch_report([_res("Grade A", 90)])
    csv_text = batch_report_to_csv(rep)
    assert "Sample,Grade,Score" in csv_text
    assert "SUMMARY" in csv_text
    assert "Grade A" in csv_text


def test_error_entry_gets_error_status_not_success():
    """A failed analysis must be marked ERROR, never a graded SUCCESS line."""
    rep = build_batch_report([{"name": "bad.jpg", "result": {}, "weight_kg": 2.0, "error": "Corrupted image"}])
    assert rep.items[0]["status"] == "ERROR"
    assert rep.items[0]["grade"] == "Error"
    assert rep.error_count == 1


def test_graded_weight_excludes_manual_review_and_errors():
    """Only genuinely graded lines contribute weight to the lot."""
    rep = build_batch_report([
        _res("Grade A", 90),  # weight 1.0, graded
        {"name": "m.jpg", "result": {"grade": "Manual Review", "overall_score": None,
                                     "status": "MANUAL_REVIEW_REQUIRED", "defects_detected": [],
                                     "color_type": "Unknown"}, "weight_kg": 3.0},
        {"name": "bad.jpg", "result": {}, "weight_kg": 5.0, "error": "Corrupted image"},
    ])
    assert rep.total_weight_kg == 1.0
    assert rep.graded_count == 1
    assert rep.manual_review_count == 1
    assert rep.error_count == 1
    assert "Error" not in rep.grade_counts
