from statistics import median


def _corrected(row):
    fields = row.record.reported
    if None in (fields["span_temp"], fields["reading"], fields["design"]):
        return None
    return fields["reading"] - (fields["span_temp"] - 19) * 0.58 - fields["design"]


def context(current, neighbors, old, score):
    current_value = _corrected(current)
    survey = current.record.reported
    comparable = [
        res
        for point in old
        if (res := _corrected(point)) is not None
        and abs(point.record.clock - current.record.clock) <= 12
    ]
    observed_shift = median(comparable) if len(comparable) >= 8 else None
    recurrence = [
        point
        for point in neighbors
        if abs(point.record.day - current.record.day) <= 2
        and point.record.reported.get("occupied") == 1
    ]
    closure_overlap = sum(
        point.record.clock // 4 == current.record.clock // 4 for point in recurrence
    )
    weight = survey["axles"] or 0
    reserve = (survey["lane_min"] or 0) - 25 - 10 * int(weight > 100)
    supervised = closure_overlap >= 1 and reserve < 8 and weight > 85
    return {
        "decision": "与已占车道相邻，送检需重新协调封闭" if supervised else "",
        "support": len(comparable),
        "thermal_residual_mm": current_value,
        "peer_displacement_mm": observed_shift,
        "coincident_lane_blocks": closure_overlap,
        "closure_headroom_min": reserve,
    }
