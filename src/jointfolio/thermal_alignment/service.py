from collections import defaultdict
from dataclasses import replace
from statistics import median

from ..joint_register.contracts import Observation
from ..settings import FIELD_BOUNDS, GROUPS, REPORT_LAG, SIGNAL_NAMES
from .contracts import FeatureBank, Scale, Signal
from .coverage import fit_audit, measure_sensitivity, reference_summary
from .domain import (
    apply_reading_correction,
    calibrated_reading,
    correct_reading,
    default_fills,
    domain_factors,
    net_width,
    robust_scale,
    usable_report,
)


MIN_GROUP = 14


def make_scale(rows: list[Observation], backup: dict[str, float]) -> Scale:
    fills = {}
    for field in FIELD_BOUNDS:
        seen = [
            item.reported[field]
            for item in rows
            if item.reported.get(field) is not None
        ]
        fills[field] = median(seen) if seen else backup[field]
    vectors = [domain_factors(usable_report(item.reported, fills)) for item in rows]
    pivots = (
        [robust_scale(list(column)) for column in zip(*vectors)]
        if vectors
        else [(0.0, 1.0)] * len(SIGNAL_NAMES)
    )
    centers, slopes = zip(*pivots)
    return Scale(fills, centers, slopes, len(rows))


def learn_bank(observations: tuple[Observation, ...], cutoff: int) -> FeatureBank:
    # 拟合统计量使用决定时已见且训练冻结前到达的测量。
    history = [
        item
        for item in observations
        if item.day < cutoff
        and item.arrived < cutoff
        and item.arrived <= item.day + REPORT_LAG
    ]
    by_group = defaultdict(list)
    for item in history:
        by_group[item.group].append(item)
    population = {name: len(by_group[name]) for name in GROUPS}
    global_scale = make_scale(history, default_fills())
    local = {
        group: make_scale(rows, global_scale.fills)
        for group, rows in by_group.items()
        if len(rows) >= MIN_GROUP
    }
    return FeatureBank(cutoff, global_scale, local, population)


def encode(record: Observation, bank: FeatureBank) -> Signal:
    # 中心与尺度用同一份全局参考；分组尺度用于缺测插补，保留物理组间差别。
    subgroup = bank.group_scales.get(record.group)
    scale = subgroup or bank.global_scale
    reported = usable_report(record.reported, scale.fills)
    raw = domain_factors(reported)
    norm = tuple(
        max(-12.0, min(12.0, (value - center) / step))
        for value, center, step in zip(
            raw, bank.global_scale.centers, bank.global_scale.slopes
        )
    )
    missing = tuple(key for key, value in record.reported.items() if value is None)
    return Signal(
        record,
        raw,
        norm,
        missing,
        record.group if subgroup else "全域",
        fills=scale.fills,
        centers=bank.global_scale.centers,
        scales=bank.global_scale.slopes,
    )


def signal_at_knowledge_cutoff(signal: Signal, ruler_book, cutoff: int) -> Signal:
    """Recompute the reading feature with only calibrations confirmed by cutoff."""
    if ruler_book is None or not getattr(signal.record, "ruler_id", None):
        return signal
    book = ruler_book.at(cutoff) if hasattr(ruler_book, "at") else ruler_book
    verdict = book.verdict_for_observation(signal.record)
    reported = dict(signal.record.reported)
    if verdict.status == "APPLIED" and verdict.corrected_reading is not None:
        reported["reading"] = verdict.corrected_reading
    else:
        # Before a correction is confirmed/resolved, folds use the raw reading.
        reported["reading"] = signal.record.raw_reading
    fills = signal.fills or default_fills()
    filled = usable_report(reported, fills)
    raw = domain_factors(filled)
    if signal.centers is not None and signal.scales is not None:
        norm = tuple(
            max(-12.0, min(12.0, (value - center) / step))
            for value, center, step in zip(raw, signal.centers, signal.scales)
        )
    else:
        norm = signal.normalized
    missing = tuple(key for key, value in reported.items() if value is None)
    record = replace(
        signal.record,
        reported=reported,
        ruler_status=verdict.status,
        ruler_reason=verdict.reason,
        ruler_basis=verdict.basis,
    )
    return replace(
        signal,
        record=record,
        vector=raw,
        normalized=norm,
        missing=missing,
        fills=fills,
    )


def trace(signal: Signal) -> dict:
    measurements = dict(signal.record.reported)
    if getattr(signal.record, "ruler_id", None) and signal.record.raw_reading is not None:
        measurements["reading"] = signal.record.raw_reading
    return {
        "case_id": signal.record.case_id,
        "feature_reference": signal.reference,
        "missing": list(signal.missing),
        "features": dict(zip(SIGNAL_NAMES, signal.vector)),
        "standardized": dict(zip(SIGNAL_NAMES, signal.normalized)),
        "measurements": measurements,
        "net_width_reading": signal.record.reported.get("reading"),
        "decision_day": signal.record.day + REPORT_LAG,
    }


def ranges(signals: list[Signal]) -> dict:
    evidence = {}
    for index, name in enumerate(SIGNAL_NAMES):
        column = sorted(item.vector[index] for item in signals)
        if column:
            evidence[name] = {
                "min": column[0],
                "median": median(column),
                "max": column[-1],
            }
    return evidence
