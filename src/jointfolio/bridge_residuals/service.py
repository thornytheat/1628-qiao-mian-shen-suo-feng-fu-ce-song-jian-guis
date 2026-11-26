from collections import defaultdict
from dataclasses import replace

from ..joint_register.service import known_labels
from ..joint_sen_fit.service import score
from ..settings import METRIC_LABEL, TARGET
from ..thermal_alignment.service import signal_at_knowledge_cutoff
from .contracts import Assessment, Folds, Paired, ScoreCard
from .evaluation import apply_calibration, calibrate, evaluate, percentile


def split(as_of):
    return Folds(as_of - 63, as_of - 34, as_of - 11, as_of)


def paired(signals, intake, after, before, reference_day, model):
    labels = known_labels(intake, reference_day)
    ruler_book = getattr(intake, "ruler_book", None)
    rows = []
    for item in signals:
        if not (
            after <= item.record.day < before
            and item.record.arrived <= reference_day
            and item.record.case_id in labels
        ):
            continue
        effective = signal_at_knowledge_cutoff(item, ruler_book, reference_day)
        rows.append(
            Paired(
                effective.record.case_id,
                effective.record.group,
                labels[effective.record.case_id].value,
                score(model, effective),
                score(model, effective, baseline=True),
                labels[effective.record.case_id].occurred,
            )
        )
    return rows


def backcheck(signals, intake, bounds, model):
    calibration = paired(
        signals,
        intake,
        bounds.train_before,
        bounds.calibrate_before,
        bounds.calibrate_before - 1,
        model,
    )
    holdout = paired(
        signals,
        intake,
        bounds.calibrate_before,
        bounds.validate_before,
        bounds.snapshot - 1,
        model,
    )
    steps = calibrate(calibration, model.incumbent)
    evidence = [
        replace(row, predicted=apply_calibration(row.predicted, steps))
        for row in holdout
    ]
    radius = (
        None
        if TARGET in {"binary", "anomaly"} or len(calibration) < 16
        else percentile(
            [abs(row.actual - row.predicted) for row in calibration if row.occurred],
            0.80,
        )
    )
    overall = evaluate(evidence, radius)
    loss, benchmark = overall["loss"], overall["reference_loss"]
    if TARGET == "anomaly":
        rank = overall["auc"]
        passed = rank is not None and rank >= 0.48
    else:
        passed = (
            loss is not None
            and benchmark is not None
            and loss <= 1.25 * benchmark + 0.05
        )
    grouped = defaultdict(list)
    for row in evidence:
        grouped[row.group].append(row)
    report = {
        "metric": METRIC_LABEL,
        "overall": overall,
        "groups": {k: evaluate(rows, radius) for k, rows in sorted(grouped.items())},
        "calibration_cases": len(calibration),
        "holdout_cases": len(holdout),
        "holdout_days": [bounds.calibrate_before, bounds.validate_before - 1],
        "label_cutoffs": [
            bounds.train_before - 1,
            bounds.calibrate_before - 1,
            bounds.snapshot - 1,
        ],
        "fold_start": [
            bounds.train_before,
            bounds.calibrate_before,
            bounds.validate_before,
        ],
        "calibration_points": len(steps),
        "interval_radius": radius,
    }
    gate = (
        passed
        and model.state is not None
        and len(calibration) >= 16
        and overall["observed_support"] >= 16
    )
    return Assessment(steps, radius, gate, report)


def score_card(model, assessment, signal):
    estimate = apply_calibration(score(model, signal), assessment.calibration)
    prior = score(model, signal, baseline=True)
    lower = (
        max(0.0, estimate - assessment.radius)
        if assessment.radius is not None
        else None
    )
    upper = estimate + assessment.radius if assessment.radius is not None else None
    return ScoreCard(signal, estimate, prior, lower, upper)
