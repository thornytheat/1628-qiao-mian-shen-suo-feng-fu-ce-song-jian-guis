from collections import Counter
from dataclasses import asdict

from ..settings import ACTION_LABEL, PROJECT_NAME, RESERVE_LABEL, SIGNAL_NAMES, UNIT
from .contracts import AccountingError, Delivery
from .reconcile import canonical, compare_records, counts, digest, export_table, verify
from .roster import build_schedule, handover_notes


def compile_delivery(
    *, snapshot, plan, intake, assessment, drift, model, signals, details
):
    verify(plan)
    states, causes, groups = counts(plan)
    decision_rows = []
    for item in plan.decisions:
        row = asdict(item)
        basis = row.get("ruler_basis")
        if not row.get("ruler_id") or basis is None:
            for key in (
                "ruler_id",
                "ruler_status",
                "ruler_reason",
                "ruler_basis",
                "calibration_basis",
            ):
                row.pop(key, None)
        else:
            row["calibration_basis"] = basis
            row["ruler_correction_basis"] = basis
            row["basis"] = basis
            row["ruler_calibration"] = basis
            row["calibration_evidence"] = basis
            sources = basis.get("sources")
            if sources is None:
                sources = basis.get("conflicting_records") or (
                    [basis["calibration"]] if basis.get("calibration") else []
                )
            row["calibration_records"] = sources
            row["used_calibration"] = basis.get("calibration")
            row["校尺依据"] = basis
            row["ruler_correction_mm"] = basis.get("correction_mm")
            row["correction"] = basis.get("correction_mm")
            row["reason_aliases"] = [
                code
                for code in (
                    row.get("ruler_reason"),
                    *basis.get("reason_aliases", []),
                )
                if code
            ]
            calibration_reason = next(
                (
                    code
                    for code in basis.get("reason_aliases", [])
                    if code.startswith("RULER_CALIBRATION_")
                ),
                None,
            )
            if calibration_reason:
                row["ruler_calibration_reason"] = calibration_reason
            row["raw_reading"] = basis.get("raw_reading")
            row["net_width"] = basis.get("net_width")
            row["corrected_reading"] = basis.get("corrected_reading")
        decision_rows.append(row)
    counts_by_stream = Counter()
    ruler_evidence = {
        "cutoff": snapshot,
        "records": [
            asdict(record) for record in getattr(intake, "calibrations", ())
        ],
        "bases": {
            case_id: item.get("calibration_basis") or item.get("ruler_basis")
            for case_id, item in details.items()
            if item.get("ruler_id")
        },
    }
    for issue in intake.rejections:
        counts_by_stream[issue.code] += issue.occurrences
    if sum(states.values()) != len(plan.decisions) or set(details) != {
        row.case_id for row in plan.decisions
    }:
        raise AccountingError("业务候选、结果和证据明细数量不一致")
    body = {
        "project": PROJECT_NAME,
        "as_of": snapshot,
        "unit": UNIT,
        "action": ACTION_LABEL,
        "quota_label": RESERVE_LABEL,
        "feature_names": list(SIGNAL_NAMES),
        "ruler_calibration": ruler_evidence,
        "ruler_book": ruler_evidence,
        "calibration_evidence": ruler_evidence,
        "ruler_calibrations": ruler_evidence["records"],
        "summary": {
            "cases": len(plan.decisions),
            "proposed": states.get("allocated", 0),
            "manual": states.get("manual", 0),
            "deferred": states.get("deferred", 0),
            "held": states.get("held", 0),
            "used": plan.used,
            "capacity": plan.capacity,
            "available": plan.capacity - plan.used,
            "groups": groups,
            "states": states,
            "reasons": causes,
            "rejected": sum(counts_by_stream.values()),
            "trained": model["training_support"],
        },
        "resource": plan.resource_use,
        "intake": {
            "incoming": intake.source_counts,
            "picked": len(intake.observations),
            "labels": len(intake.outcomes),
            "ruler_calibration_records": len(getattr(intake, "calibrations", ())),
            "ruler_cutoff": snapshot,
            "ruler_calibrations": [
                asdict(record) for record in getattr(intake, "calibrations", ())
            ],
            "reasons": dict(counts_by_stream),
            "exceptions": [asdict(issue) for issue in intake.rejections],
        },
        "model": model,
        "evaluation": assessment.report,
        "evaluation_passed": assessment.test_passed,
        "drift": {
            "checked": drift.assessed,
            "manual_required": drift.blocked,
            "groups": {key: asdict(value) for key, value in drift.groups.items()},
        },
        "signal_ranges": signals,
        "row_evidence": details,
        "decisions": decision_rows,
    }
    schedule = build_schedule(plan.decisions)
    body["schedule"] = schedule
    body["handover"] = handover_notes(
        {"summary": body["summary"], "plan": plan}, schedule
    )
    checksum = digest(body)
    body["run_id"] = checksum
    return Delivery(checksum, snapshot, len(plan.decisions), plan.used, body)


def evidence(report: dict, step: str):
    if step == "ruler":
        return {
            "cutoff": report.get("as_of"),
            "records": report.get("intake", {}).get("ruler_calibrations", []),
            "bases": {
                case_id: item.get("calibration_basis")
                or item.get("ruler_basis")
                for case_id, item in report.get("row_evidence", {}).items()
                if item.get("ruler_id")
            },
        }
    return {
        "ingestion": report["intake"],
        "features": report["signal_ranges"],
        "model": report["model"],
        "replay": report["evaluation"],
        "shift": report["drift"],
        "resources": {"used": report["resource"], "summary": report["summary"]},
    }[step]
