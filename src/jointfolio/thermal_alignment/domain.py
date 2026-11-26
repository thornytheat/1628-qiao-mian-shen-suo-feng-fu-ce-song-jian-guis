from math import isfinite
from statistics import median

from ..settings import FIELD_BOUNDS, SIGNAL_NAMES


def apply_reading_correction(
    reading: float | None, correction_mm: float = 0.0
) -> float | None:
    """把带符号校尺差加到尺读数上，得到训练/回放/推理共用的净宽。"""
    if reading is None:
        return None
    return round(float(reading) + float(correction_mm), 9)


correct_reading = apply_reading_correction
calibrated_reading = apply_reading_correction
net_width = apply_reading_correction


def domain_factors(filled: dict[str, float]) -> tuple[float, ...]:
    """桥面伸缩缝复测送检的业务量从原始单位换算，顺序固定供训练和回放共用。"""
    reading = filled["reading"]
    span_temp = filled["span_temp"]
    design = filled["design"]
    axles = filled["axles"]
    history = filled["history"]
    values = (
        abs(reading - (design + (span_temp - 19) * 0.58)) / 30,
        (span_temp + 10) / 57,
        axles / 220,
        history / 14,
    )
    if len(values) != len(SIGNAL_NAMES) or any(not isfinite(value) for value in values):
        raise ValueError("特征计算出现非有限值或字段数不符")
    return values


def robust_scale(values: list[float]) -> tuple[float, float]:
    center = median(values)
    mad = median([abs(v - center) for v in values])
    if mad <= 1e-9:
        # 常量特征使用单位幅度；单个异常读数不应把通用尺度放大。
        return center, 1.0
    return center, max(mad * 1.4826, 1e-6)


def default_fills() -> dict[str, float]:
    return {field: (low + high) / 2 for field, (low, high) in FIELD_BOUNDS.items()}


def usable_report(
    measurements: dict[str, float | None], fallback: dict[str, float]
) -> dict[str, float]:
    return {
        field: fallback[field]
        if measurements.get(field) is None
        else measurements[field]
        for field in FIELD_BOUNDS
    }
