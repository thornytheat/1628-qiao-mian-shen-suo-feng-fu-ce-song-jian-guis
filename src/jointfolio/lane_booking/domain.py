from math import ceil

from ..settings import ACTION_LABEL, FIELD_BOUNDS
from .contracts import Request


def project_request(card, gate, calendar_day=None) -> Request:
    record = card.signal.record
    values = {
        key: record.reported[key]
        if record.reported.get(key) is not None
        else (lo + hi) / 2
        for key, (lo, hi) in FIELD_BOUNDS.items()
    }
    axles = values["axles"]
    lane_min = values["lane_min"]
    occupied = values["occupied"]
    score = card.estimate if gate.allowed else card.prior
    blocked = occupied >= 1 or lane_min < 22
    priority = max(0, score - 1.7) * (1 + axles / 170)
    units = 1 + int(axles >= 120) + int(score > 4)
    status = "candidate"
    reason = "RULE_ELIGIBLE"
    details = ()
    if blocked and all(
        record.reported.get(k) is not None for k in ("lane_min", "occupied")
    ):
        status, reason, details = "held", "BUSINESS_LOCK", ("车道已占用或许可窗口过短",)
    elif not gate.allowed:
        status, reason, details = "manual", "TRUST_REVIEW", gate.reasons
    elif priority <= 0:
        status, reason, details = "monitor", "BELOW_ACTION", ("预计收益未达到处置阈值",)

    return Request(
        record.case_id,
        record.group,
        record.day if calendar_day is None else calendar_day,
        record.clock,
        record.group,
        units,
        round(score, 7),
        card.lower if gate.allowed else None,
        card.upper if gate.allowed else None,
        round(priority, 7),
        gate.source,
        status,
        reason,
        details,
        ACTION_LABEL,
    )


def resource_limit(day_budget: int) -> int:
    return max(1, day_budget * 2 // 3)
