from collections import defaultdict
from math import isfinite

REVIEW_NAME = "热差与封闭窗口"
IMPACT_NAME = "重轴修正位移/mm"
HEADROOM_NAME = "车道剩余许可/min"
OVERRIDE_NOTE = "重轴流量偏高，封闭时窗不足"


def operational_check(readings, estimate):
    """同一个净宽在冬夏取值不同，送检单保留校正前读数与许可。"""
    reading = readings["reading"]
    span_temp = readings["span_temp"]
    design = readings["design"]
    axles = readings["axles"]
    lane_min = readings["lane_min"]
    impact = abs(reading - (design + (span_temp - 19) * 0.58)) * (1 + axles / 400)
    headroom = lane_min - (20 + 12 * int(axles > 120))
    override = bool(axles > 160 and lane_min < 33)
    if not isfinite(impact) or not isfinite(headroom):
        raise ValueError("业务复核的观测量超出计算范围")
    return {
        "name": REVIEW_NAME,
        "impact_label": IMPACT_NAME,
        "headroom_label": HEADROOM_NAME,
        "impact": round(impact, 6),
        "headroom": round(headroom, 6),
        "requires_operator": override,
        "reason": OVERRIDE_NOTE if override else "",
    }


def summarize_workload(actions, evidence):
    distribution = defaultdict(
        lambda: {
            "selected_impact": 0.0,
            "selected": 0,
            "tight_window": 0,
            "needs_operator": 0,
        }
    )
    for action in actions:
        branch = distribution[action.cohort]
        current = evidence[action.case_id]["operational_check"]
        if action.status == "allocated":
            branch["selected"] += 1
            branch["selected_impact"] += current["impact"]
            if current["headroom"] < 0:
                branch["tight_window"] += 1
        if current["requires_operator"]:
            branch["needs_operator"] += 1
    return {
        name: {**data, "selected_impact": round(data["selected_impact"], 4)}
        for name, data in sorted(distribution.items())
    }
