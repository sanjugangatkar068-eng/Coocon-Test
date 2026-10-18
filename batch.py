"""
SilkCocoonAI - Batch Lot Aggregation (batch.py)

Grades a whole lot of cocoon photos at once and rolls the individual results up
into a single, auditable lot report: grade distribution, weighted average score,
defect frequency, and an overall lot recommendation.

Designed to sit on top of scoring.calculate_cocoon_grade() - it consumes the
plain dict form of CocoonGradingResult, so it stays framework-agnostic and easy
to unit test.
"""

import csv
import io
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

# Worst-to-best ordering used for lot-level rollups.
GRADE_RANK = {
    "Reject": 0,
    "Manual Review": 1,
    "Grade C": 2,
    "Grade B": 3,
    "Grade A": 4,
}


@dataclass
class BatchItem:
    """One graded photo inside a batch."""
    name: str
    grade: str
    score: Optional[float]
    color_type: str
    defects: List[str] = field(default_factory=list)
    status: str = "SUCCESS"
    weight_kg: float = 0.0
    error: str = ""


@dataclass
class BatchReport:
    """Aggregated outcome for a lot of cocoon photos."""
    total_images: int = 0
    graded_count: int = 0
    manual_review_count: int = 0
    error_count: int = 0
    grade_counts: Dict[str, int] = field(default_factory=dict)
    average_score: Optional[float] = None
    weighted_average_score: Optional[float] = None
    total_weight_kg: float = 0.0
    defect_frequency: Dict[str, int] = field(default_factory=dict)
    dominant_grade: str = "Manual Review"
    worst_grade: str = "Manual Review"
    lot_recommendation: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _rank(grade: str) -> int:
    return GRADE_RANK.get(grade, 1)


def build_batch_report(entries: List[Dict[str, Any]]) -> BatchReport:
    """
    Build a BatchReport from graded entries.

    Each entry: {
        "name": str,
        "result": dict,            # CocoonGradingResult.to_dict() (optional)
        "weight_kg": float,        # optional weight for this sample
        "error": str,              # optional error string if analysis failed
    }
    """
    report = BatchReport(total_images=len(entries or []))
    items: List[BatchItem] = []
    grade_counts: Dict[str, int] = {}
    defect_frequency: Dict[str, int] = {}
    # Entries in these states must never be priced or weighted as a graded lot line.
    non_gradable = {"", "manual review", "error", "n/a", "unknown", "none"}

    scored: List[float] = []
    weighted_sum = 0.0
    weight_total = 0.0
    total_weight = 0.0

    for entry in entries or []:
        name = str(entry.get("name", "sample"))
        try:
            weight = float(entry.get("weight_kg", 0) or 0)
        except (TypeError, ValueError):
            weight = 0.0

        err = entry.get("error") or ""
        result = entry.get("result") or {}

        # A failed analysis is an error line, never a graded line.
        if err and not result:
            report.error_count += 1
            items.append(BatchItem(name=name, grade="Error", score=None, status="ERROR",
                                   color_type="Unknown", weight_kg=weight, error=err))
            continue

        grade = str(result.get("grade", "Manual Review"))
        status = str(result.get("status", ""))
        score = result.get("overall_score")
        grade_key = grade.strip().lower()

        # Decide the line's true state. Anything without a score, or in a
        # non-gradable state, must never be counted as a graded lot line.
        if grade_key == "error":
            line_status = "ERROR"
        elif score is None or status == "MANUAL_REVIEW_REQUIRED" or grade_key in non_gradable:
            line_status = "MANUAL_REVIEW_REQUIRED"
        else:
            line_status = "SUCCESS"

        color = str(result.get("color_type", "Unknown"))
        defects = [str(d).lower() for d in (result.get("defects_detected") or [])]

        for d in defects:
            defect_frequency[d] = defect_frequency.get(d, 0) + 1

        if line_status == "ERROR":
            report.error_count += 1
        else:
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
            if line_status == "MANUAL_REVIEW_REQUIRED":
                report.manual_review_count += 1
            else:
                report.graded_count += 1
                total_weight += weight  # only graded weight counts toward the lot
                scored.append(float(score))
                effective_weight = weight if weight > 0 else 1.0
                weighted_sum += float(score) * effective_weight
                weight_total += effective_weight

        items.append(BatchItem(
            name=name, grade=grade, score=(round(float(score), 1) if score is not None else None),
            color_type=color, defects=defects, status=line_status, weight_kg=weight, error="",
        ))

    report.grade_counts = grade_counts
    report.defect_frequency = defect_frequency
    report.total_weight_kg = round(total_weight, 3)
    report.items = [asdict(i) for i in items]

    if scored:
        report.average_score = round(sum(scored) / len(scored), 1)
    if weight_total > 0:
        report.weighted_average_score = round(weighted_sum / weight_total, 1)

    # Rollups
    if grade_counts:
        report.dominant_grade = max(grade_counts.items(), key=lambda kv: kv[1])[0]
        report.worst_grade = min(grade_counts.keys(), key=_rank)
    report.lot_recommendation = _lot_recommendation(report)

    return report


def _lot_recommendation(report: BatchReport) -> str:
    """A short, honest lot-level action line derived from the aggregate."""
    if report.graded_count == 0:
        return ("No sample could be graded automatically. Retake clearer, well-lit photos "
                "of the cocoons before sending the lot to market.")

    reject_share = report.grade_counts.get("Reject", 0) / max(1, report.graded_count)
    a_share = report.grade_counts.get("Grade A", 0) / max(1, report.graded_count)
    weighted = report.weighted_average_score or 0.0

    if report.worst_grade == "Reject" and reject_share >= 0.3:
        return ("High defect load: a large share of samples are Reject grade. "
                "Sort out pierced/melted units before auction to avoid a blanket price cut.")
    if weighted >= 85 and a_share >= 0.6:
        return "Premium lot. Submit as a single Grade A consignment to capture top reeling prices."
    if weighted >= 70:
        return "Sound commercial lot. Suitable for standard reeling; a light sort improves the average grade."
    if weighted >= 50:
        return "Mixed/coarse lot. Sort into grade-wise bags and expect a price discount."
    return "Low-grade lot. Divert to spun silk / dupion channels rather than fine reeling."


def batch_report_to_csv(report: BatchReport) -> str:
    """Serialise the per-item rows of a BatchReport to CSV text."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Sample", "Grade", "Score", "Color Type", "Defects", "Weight_kg", "Status", "Error"])
    for item in report.items:
        writer.writerow([
            item.get("name", ""),
            item.get("grade", ""),
            "" if item.get("score") is None else item.get("score"),
            item.get("color_type", ""),
            "; ".join(item.get("defects", []) or []),
            item.get("weight_kg", 0),
            item.get("status", ""),
            item.get("error", ""),
        ])
    # Summary trailer
    writer.writerow([])
    writer.writerow(["SUMMARY"])
    writer.writerow(["Total images", report.total_images])
    writer.writerow(["Graded", report.graded_count])
    writer.writerow(["Manual review", report.manual_review_count])
    writer.writerow(["Errors", report.error_count])
    writer.writerow(["Average score", report.average_score if report.average_score is not None else ""])
    writer.writerow(["Weighted average score", report.weighted_average_score if report.weighted_average_score is not None else ""])
    writer.writerow(["Dominant grade", report.dominant_grade])
    writer.writerow(["Worst grade", report.worst_grade])
    writer.writerow(["Total weight (kg)", report.total_weight_kg])
    writer.writerow(["Lot recommendation", report.lot_recommendation])
    return buffer.getvalue()
