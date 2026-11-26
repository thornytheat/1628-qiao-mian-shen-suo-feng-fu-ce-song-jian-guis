from itertools import combinations
from math import fsum
from statistics import median


def slope_by_pairs(points):
    slopes = []
    for (x1, y1), (x2, y2) in combinations(points, 2):
        gap = x2 - x1
        if abs(gap) > 0.005:
            slopes.append((y2 - y1) / gap)
    return median(slopes) if slopes else 0.0


def train(rows):
    history = sorted(
        rows,
        key=lambda row: (
            row.signal.record.group,
            row.signal.record.day,
            row.signal.record.case_id,
        ),
    )
    step = max(1, len(history) // 62)
    work = history[::step][:85]
    y = [row.y for row in work]
    coordinates = [row.raw for row in work]
    components = list(zip(*coordinates))
    slope = [0.0] * len(components)
    # 逆温差参考归一到热偏离项之后再拟合，避免用总位移冒充异常量。
    for _ in range(4):
        for axis, column in enumerate(components):
            residual = [
                value
                - fsum(
                    c * x for pos, (c, x) in enumerate(zip(slope, row)) if pos != axis
                )
                for value, row in zip(y, coordinates)
            ]
            slope[axis] = slope_by_pairs(list(zip(column, residual)))
    origin = median(
        [
            value - fsum(c * x for c, x in zip(slope, row))
            for value, row in zip(y, coordinates)
        ]
    )
    median_error = median(
        [
            abs(value - origin - fsum(c * x for c, x in zip(slope, row)))
            for value, row in zip(y, coordinates)
        ]
    )
    return {
        "slope": tuple(slope),
        "temperature_origin": origin,
        "chosen_joints": len(work),
        "median_error": median_error,
    }


def infer(state, signal):
    projection = fsum(
        slope * reading for slope, reading in zip(state["slope"], signal.vector)
    )
    return state["temperature_origin"] + projection


def explain(state):
    return {
        "thermal_adjusted_slopes": state["slope"],
        "joint_subset": state["chosen_joints"],
        "robust_distance_mm": state["median_error"],
        "intercept": state["temperature_origin"],
    }
