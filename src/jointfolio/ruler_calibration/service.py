from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
import math
import re
from typing import Any, Iterable

from .contracts import (
    REASON_ALIASES,
    REASON_CONFLICT,
    REASON_INVALID,
    REASON_LATE,
    REASON_MISSING,
    STATUS_CONFLICT,
    STATUS_MISSING,
    STATUS_OK,
    STATUS_UNTRACKED,
    CalibrationRecord,
    RulerVerdict,
)


CALIBRATION_STREAM_KEYS = frozenset(
    {
        "ruler_calibrations",
        "ruler_calibration",
        "ruler_corrections",
        "ruler_correction",
        "ruler_differences",
        "ruler_difference",
        "ruler_diffs",
        "ruler_offsets",
        "ruler_offset",
        "ruler_records",
        "ruler_ledger",
        "ruler_book",
        "rulers",
        "calibrations",
        "calibration_records",
        "calibration",
        "calibration_book",
        "calibration_ledger",
        "gauge_calibrations",
        "gauge_corrections",
        "gauge_records",
        "gauges",
        "tape_calibrations",
        "tape_corrections",
        "scale_calibrations",
        "scale_corrections",
        "instrument_calibrations",
        "instrument_records",
        "measurement_calibrations",
        "correction_records",
        "corrections",
        "offsets",
    }
)

_CALIBRATION_KEY_RE = re.compile(
    r"ruler|calibr|gauge|tape|scale|meter|instrument|verification|"
    r"correction|offset|jiaochi|chicha|chizhun|校尺",
    re.IGNORECASE,
)

_RULER_ID_KEYS = (
    "ruler_id",
    "ruler_code",
    "ruler_no",
    "ruler_number",
    "ruler",
    "gauge_id",
    "meter_id",
    "tape_id",
    "scale_id",
    "instrument_id",
    "ruler_sn",
    "tool_sn",
    "serial_number",
    "serial",
    "尺编号",
    "尺号",
)

_CORRECTION_KEYS = (
    "correction_mm",
    "ruler_correction_mm",
    "calibration_correction_mm",
    "correction_value",
    "ruler_correction",
    "calibration_correction",
    "correction",
    "offset_mm",
    "ruler_offset_mm",
    "offset_value",
    "ruler_offset",
    "offset",
    "adjustment_mm",
    "adjustment_value",
    "adjustment",
    "delta_mm",
    "ruler_delta_mm",
    "ruler_delta",
    "delta",
    "calibration_difference_mm",
    "ruler_difference_mm",
    "calibration_diff_mm",
    "difference_mm",
    "ruler_difference",
    "calibration_difference",
    "calibration_diff",
    "difference",
    "ruler_error_mm",
    "calibration_error_mm",
    "bias_mm",
    "error_mm",
    "bias",
    "error",
    "value",
    "校尺差",
    "校正值",
    "改正值",
)

_CONFIRMED_KEYS = (
    "confirmed_day",
    "confirmation_day",
    "confirm_day",
    "confirmed_on",
    "confirmed_at_day",
    "confirmed_date",
    "confirmed_at",
    "confirmed",
    "confirmation",
    "available",
    "arrived_day",
    "arrival_day",
    "received_day",
    "received",
    "arrived",
    "as_of",
    "cutoff_day",
    "visible_day",
    "校尺确认日",
    "确认日",
    "确认时间",
)

_EXACT_DAY_KEYS = (
    "measurement_day",
    "on_day",
    "valid_on_day",
    "valid_on",
    "applies_on",
    "day",
)

_EFFECTIVE_START_KEYS = (
    "effective_from_day",
    "effective_start_day",
    "effective_start",
    "valid_from_day",
    "valid_start_day",
    "start_day",
    "period_start_day",
    "period_start",
    "valid_period_start",
    "from_day",
    "effective_from",
    "valid_from",
    "effective_day",
    "start",
    "from",
)

_END_KEYS = (
    "effective_to_day",
    "effective_end_day",
    "effective_end",
    "valid_to_day",
    "valid_end_day",
    "end_day",
    "period_end_day",
    "period_end",
    "valid_period_end",
    "until_day",
    "to_day",
    "effective_to",
    "valid_to",
    "end",
    "until",
    "to",
)

_PERIOD_KEYS = (
    "period_id",
    "valid_period",
    "effective_period",
    "validity",
    "range",
    "period",
    "slot",
    "window",
    "term",
)


def normalized_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9一-鿿]", "", str(key).strip().lower())


def is_calibration_stream_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    compact = normalized_key(key)
    known = {normalized_key(item) for item in CALIBRATION_STREAM_KEYS}
    if compact in known:
        return True
    return bool(_CALIBRATION_KEY_RE.search(key))


def calibration_streams(packet: dict[str, Any]) -> list[tuple[str, list[dict]]]:
    streams = []
    for key, value in packet.items():
        if not is_calibration_stream_key(key):
            continue
        if isinstance(value, list):
            streams.append((key, value))
        elif isinstance(value, dict):
            # A singleton calibration envelope is tolerated at packet level.
            rows = value.get("records") or value.get("items") or value.get("rows")
            if isinstance(rows, list):
                streams.append((key, rows))
            elif value:
                streams.append((key, [value]))
    return streams


def _embedded_calibration_rows(packet: dict[str, Any]) -> list[dict]:
    rows: list[dict] = []
    observations = packet.get("observations")
    if not isinstance(observations, list):
        return rows
    correction_terms = (
        "correction",
        "offset",
        "delta",
        "difference",
        "bias",
        "error",
        "校尺差",
    )
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        ruler_id = extract_ruler_id(observation)
        if not ruler_id:
            continue
        envelope = None
        for key in (
            "ruler_calibration",
            "calibration",
            "calibration_record",
            "ruler_record",
        ):
            value = observation.get(key)
            if isinstance(value, dict):
                envelope = dict(value)
                break
            if isinstance(value, list):
                rows.extend(row for row in value if isinstance(row, dict))
        if envelope is not None:
            envelope.setdefault("ruler_id", ruler_id)
            rows.append(envelope)
            continue
        has_correction = any(
            any(term in normalized_key(key) for term in correction_terms)
            for key in observation
        )
        if has_correction:
            row = dict(observation)
            row.setdefault("ruler_id", ruler_id)
            row.setdefault("day", observation.get("day"))
            row.setdefault("confirmed_day", observation.get("arrived"))
            rows.append(row)
    return rows


def extract_calibration_rows(packet: dict[str, Any] | None) -> list[dict]:
    if not isinstance(packet, dict):
        return []
    rows: list[dict] = []
    for _, stream in calibration_streams(packet):
        rows.extend(row for row in stream if isinstance(row, dict))
    if not rows:
        rows.extend(_embedded_calibration_rows(packet))
    return rows


def _find(row: dict[str, Any], aliases: Iterable[str]) -> tuple[str | None, Any]:
    compact = {normalized_key(key): key for key in row}
    for alias in aliases:
        actual = compact.get(normalized_key(alias))
        if actual is not None and row.get(actual) is not None:
            return actual, row[actual]
    return None, None


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} 必须为数值")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} 必须为有限值")
    return number


def _day(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} 应是整数日")
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        value = int(value.strip())
    if not isinstance(value, int):
        raise ValueError(f"{label} 应是整数日")
    if not 1 <= value <= 36_500:
        raise ValueError(f"{label} 超出日期范围")
    return value


def _first_day(row: dict[str, Any], aliases: Iterable[str], label: str) -> int:
    last_error: ValueError | None = None
    for alias in aliases:
        key, value = _find(row, (alias,))
        if value is None:
            continue
        try:
            return _day(value, label)
        except ValueError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise ValueError(f"{label} 缺失")


def ruler_identity(value: Any) -> str | None:
    if isinstance(value, dict):
        _, inner = _find(value, ("ruler_id", "id", "code", "name"))
        value = inner
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("尺编号必须是字符串或整数")
    ruler_id = str(value).strip()
    if not ruler_id or len(ruler_id) > 64:
        raise ValueError("尺编号缺失或长度不合法")
    return ruler_id


def extract_ruler_id(row: dict[str, Any]) -> str | None:
    _, value = _find(row, _RULER_ID_KEYS)
    if value is None and isinstance(row, dict):
        ruler_terms = (
            "ruler",
            "gauge",
            "tape",
            "meter",
            "meterid",
            "scale",
            "instrument",
            "tool",
            "measuretool",
            "toolcode",
            "toolno",
            "尺",
        )
        for key, candidate in row.items():
            compact = normalized_key(key)
            if not compact or not any(term in compact for term in ruler_terms):
                continue
            if compact in {
                "ruler",
                "gauge",
                "tape",
                "meter",
                "instrument",
                "尺编号",
                "尺号",
            }:
                value = candidate
                break
            if any(
                suffix in compact
                for suffix in (
                    "id",
                    "code",
                    "no",
                    "number",
                    "sn",
                    "serial",
                    "编号",
                    "尺号",
                )
            ) and isinstance(candidate, (str, int, dict)):
                value = candidate
                break
    return ruler_identity(value) if value is not None else None


def _fingerprint(row: dict[str, Any]) -> str:
    payload = json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:16]


def parse_calibration_row(row: dict[str, Any]) -> CalibrationRecord:
    if not isinstance(row, dict):
        raise ValueError("校尺记录必须是对象")
    ruler_id = extract_ruler_id(row)
    if ruler_id is None:
        raise ValueError("校尺记录缺少尺编号")

    value_key, raw_value = _find(row, _CORRECTION_KEYS)
    if raw_value is None:
        for key, candidate in row.items():
            compact = normalized_key(key)
            if any(
                term in compact
                for term in (
                    "correction",
                    "offset",
                    "delta",
                    "difference",
                    "diff",
                    "bias",
                    "error",
                    "校尺差",
                    "改正",
                )
            ):
                try:
                    _finite_number(candidate, "校尺差")
                except ValueError:
                    continue
                value_key, raw_value = str(key), candidate
                break
    if raw_value is None:
        # 允许直接给出校准前后读数，差值作为加性校尺差。
        _, before = _find(row, ("raw_reading", "measured_reading", "reading_before"))
        _, after = _find(
            row, ("corrected_reading", "net_reading", "reading_after", "true_reading")
        )
        if before is None or after is None:
            raise ValueError("校尺记录缺少校尺差")
        correction = _finite_number(after, "校准后净宽") - _finite_number(
            before, "校准前净宽"
        )
        value_key = "derived_reading_delta"
    else:
        if isinstance(raw_value, dict):
            _, nested = _find(
                raw_value, ("correction_mm", "mm", "value_mm", "value", "amount")
            )
            raw_value = nested
        correction = _finite_number(raw_value, "校尺差")
        # error/bias 表示尺的偏差（测量值-真值），换算成真值时取反。
        if value_key and re.search(r"error|bias", value_key, re.IGNORECASE):
            correction = -correction

    confirmed_day = _first_day(row, _CONFIRMED_KEYS, "校尺确认日")

    day = start_day = end_day = None
    period = None
    _, period_raw = _find(row, _PERIOD_KEYS)
    if isinstance(period_raw, dict):
        if start_day is None:
            for alias in _EFFECTIVE_START_KEYS:
                _, value = _find(period_raw, (alias, "start", "from"))
                if value is not None:
                    try:
                        start_day = _day(value, "校尺有效开始日")
                        break
                    except ValueError:
                        pass
        if end_day is None:
            for alias in _END_KEYS:
                _, value = _find(period_raw, (alias, "end", "to"))
                if value is not None:
                    try:
                        end_day = _day(value, "校尺有效截止日")
                        break
                    except ValueError:
                        pass
        _, period_id = _find(period_raw, ("period_id", "id", "name", "period"))
        period_raw = period_id
    if isinstance(period_raw, (list, tuple)) and len(period_raw) == 2:
        if start_day is None:
            try:
                start_day = _day(period_raw[0], "校尺有效开始日")
            except ValueError:
                pass
        if end_day is None:
            try:
                end_day = _day(period_raw[1], "校尺有效截止日")
            except ValueError:
                pass
        period_raw = None
    if period_raw is not None:
        if isinstance(period_raw, bool) or not isinstance(
            period_raw, (str, int, float)
        ):
            raise ValueError("校尺时段标识不合法")
        period = str(period_raw).strip()

    _, end_raw = _find(row, _END_KEYS)
    if end_raw is not None:
        end_day = _first_day(row, _END_KEYS, "校尺有效截止日")
    _, start_raw = _find(row, _EFFECTIVE_START_KEYS)
    if start_raw is not None:
        start_day = _first_day(row, _EFFECTIVE_START_KEYS, "校尺有效开始日")
    _, exact_raw = _find(row, _EXACT_DAY_KEYS)
    if exact_raw is not None and start_day is None:
        day = _first_day(row, _EXACT_DAY_KEYS, "校尺有效日")

    if start_day is not None and end_day is not None and start_day > end_day:
        raise ValueError("校尺有效时段起止顺序不合法")

    if period is not None:
        scope: tuple[Any, ...] = ("period", period)
    elif start_day is not None or end_day is not None:
        scope = ("range", start_day, end_day)
    elif day is not None:
        scope = ("day", day)
    else:
        scope = ("global",)

    sign_raw = row.get("sign") or row.get("correction_sign")
    if sign_raw is not None:
        if sign_raw in (-1, "-1", "subtract", "negative"):
            correction = -abs(correction)
        elif sign_raw in (1, "1", "add", "positive"):
            correction = abs(correction)

    return CalibrationRecord(
        ruler_id=ruler_id,
        correction_mm=correction,
        confirmed_day=confirmed_day,
        day=day,
        start_day=start_day,
        end_day=end_day,
        period=period,
        scope=scope,
        fingerprint=_fingerprint(row),
        raw=dict(row),
    )


def parse_calibrations(
    rows: Iterable[Any],
) -> tuple[tuple[CalibrationRecord, ...], tuple[tuple[str, str], ...]]:
    records: list[CalibrationRecord] = []
    issues: list[tuple[str, str]] = []
    for row in rows:
        try:
            if not isinstance(row, dict):
                raise ValueError("校尺记录必须是对象")
            records.append(parse_calibration_row(row))
        except ValueError as exc:
            ruler_id = "—"
            if isinstance(row, dict):
                try:
                    ruler_id = extract_ruler_id(row) or "—"
                except ValueError:
                    ruler_id = str(row.get("ruler_id", "—"))[:44]
            issues.append((str(ruler_id)[:44], str(exc)))
    records.sort(
        key=lambda item: (
            item.ruler_id,
            item.confirmed_day,
            item.scope,
            item.correction_mm,
            item.fingerprint,
        )
    )
    return tuple(records), tuple(issues)


class RulerBook:
    def __init__(
        self,
        records: tuple[CalibrationRecord, ...] | list[CalibrationRecord] = (),
        cutoff: int | None = None,
    ):
        self.records = tuple(records)
        self.cutoff = cutoff

    @classmethod
    def build(cls, rows: Iterable[Any], cutoff: int) -> "RulerBook":
        records, _ = parse_calibrations(rows)
        return cls(records, cutoff)

    def at(self, cutoff: int) -> "RulerBook":
        return RulerBook(self.records, cutoff)

    @property
    def visible(self) -> tuple[CalibrationRecord, ...]:
        if self.cutoff is None:
            return self.records
        return tuple(r for r in self.records if r.confirmed_day <= self.cutoff)

    def _covers(
        self, record: CalibrationRecord, day: int | None, period: Any = None
    ) -> tuple[bool, int]:
        if record.period is not None:
            if period is not None and str(period) == record.period:
                return True, 4
            if day is not None:
                try:
                    if record.period == str(day) or int(float(record.period)) == day:
                        return True, 3
                except (TypeError, ValueError):
                    pass
            return False, -1
        if record.day is not None:
            return (day == record.day, 3) if day is not None else (False, -1)
        if record.start_day is not None or record.end_day is not None:
            if day is None:
                return False, -1
            if record.start_day is not None and day < record.start_day:
                return False, -1
            if record.end_day is not None and day > record.end_day:
                return False, -1
            return True, 2 if record.end_day is not None else 1
        return True, 0

    def resolve(
        self,
        ruler_id: str | None,
        day: int | None = None,
        raw_reading: float | None = None,
        *,
        period: Any = None,
    ) -> RulerVerdict:
        if not ruler_id:
            value = float(raw_reading) if raw_reading is not None else None
            return RulerVerdict(
                STATUS_UNTRACKED,
                correction_mm=0.0,
                raw_reading=value,
                corrected_reading=value,
                basis={
                    "status": STATUS_UNTRACKED,
                    "applied": False,
                    "reason": "",
                    "correction_mm": 0.0,
                },
            )

        visible = list(self.visible)
        candidates: list[tuple[int, CalibrationRecord]] = []
        for record in visible:
            if record.ruler_id != ruler_id:
                continue
            matches, specificity = self._covers(record, day, period)
            if matches:
                candidates.append((specificity, record))

        def issue(status: str, reason: str, message: str) -> RulerVerdict:
            # Future confirmations are deliberately invisible here; otherwise
            # adding a late receipt would perturb the recalculated shift ticket.
            basis: dict[str, Any] = {
                "status": status,
                "applied": False,
                "reason": reason,
                "message": message,
                "ruler_id": ruler_id,
                "day": day,
                "raw_reading": raw_reading,
                "corrected_reading": None,
                "net_width": None,
                "cutoff": self.cutoff,
                "reason_aliases": REASON_ALIASES.get(reason, ()),
            }
            return RulerVerdict(
                status,
                ruler_id=ruler_id,
                reason=reason,
                raw_reading=raw_reading,
                late_records=0,
                basis=basis,
            )

        if not candidates:
            return issue(
                STATUS_MISSING,
                REASON_MISSING,
                "测量当天没有已确认且有效的校尺差",
            )

        specificity = max(score for score, _ in candidates)
        chosen_records = [r for score, r in candidates if score == specificity]
        if specificity == 1:
            latest_start = max(r.start_day for r in chosen_records)
            chosen_records = [
                r for r in chosen_records if r.start_day == latest_start
            ]

        distinct = {round(r.correction_mm, 9) for r in chosen_records}
        if len(distinct) > 1:
            verdict = issue(
                STATUS_CONFLICT,
                REASON_CONFLICT,
                "同一把尺同一时段存在相互矛盾的校尺差",
            )
            verdict.basis["conflicting_records"] = [r.raw for r in chosen_records]
            return verdict

        chosen = sorted(
            chosen_records,
            key=lambda r: (r.confirmed_day, r.fingerprint),
            reverse=True,
        )[0]
        corrected = (
            None
            if raw_reading is None
            else round(float(raw_reading) + chosen.correction_mm, 9)
        )
        basis = {
            "status": STATUS_OK,
            "applied": True,
            "reason": "",
            "ruler_id": ruler_id,
            "correction_mm": chosen.correction_mm,
            "correction": chosen.correction_mm,
            "raw_reading": raw_reading,
            "corrected_reading": corrected,
            "net_width": corrected,
            "formula": "corrected_reading = raw_reading + correction_mm",
            "confirmed_day": chosen.confirmed_day,
            "day": chosen.day,
            "start_day": chosen.start_day,
            "end_day": chosen.end_day,
            "period": chosen.period,
            "effective_on_measurement_day": day,
            "cutoff": self.cutoff,
            "calibration": chosen.raw,
            "record": chosen.raw,
            "sources": [record.raw for record in chosen_records],
            "source_count": len(chosen_records),
            "fingerprint": chosen.fingerprint,
        }
        return RulerVerdict(
            STATUS_OK,
            ruler_id=ruler_id,
            reason="",
            correction_mm=chosen.correction_mm,
            raw_reading=raw_reading,
            corrected_reading=corrected,
            confirmed_day=chosen.confirmed_day,
            effective_day=chosen.day or chosen.start_day,
            period=chosen.period,
            late_records=0,
            basis=basis,
        )

    def verdict_for_observation(self, observation: Any) -> RulerVerdict:
        ruler_id = getattr(observation, "ruler_id", None)
        raw = getattr(observation, "raw_reading", None)
        if raw is None:
            raw = observation.reported.get("reading")
        period = getattr(observation, "ruler_period", None)
        return self.resolve(
            ruler_id, observation.day, raw, period=period
        )


def apply_book(intake: Any, book: RulerBook) -> tuple[Any, dict[str, RulerVerdict]]:
    verdicts: dict[str, RulerVerdict] = {}
    updated = []
    for observation in intake.observations:
        verdict = book.verdict_for_observation(observation)
        verdicts[observation.case_id] = verdict
        changes: dict[str, Any] = {
            "ruler_status": verdict.status,
            "ruler_reason": verdict.reason,
            "ruler_basis": verdict.basis,
        }
        if observation.raw_reading is None:
            changes["raw_reading"] = observation.reported.get("reading")
        if verdict.status == STATUS_OK and verdict.corrected_reading is not None:
            reported = dict(observation.reported)
            reported["reading"] = verdict.corrected_reading
            changes["reported"] = reported
        # Missing/conflicting calibration leaves the raw measurement intact;
        # the scheduling gate turns that ruler's ticket into manual review.
        updated.append(replace(observation, **changes))
    return (
        replace(intake, observations=tuple(updated), ruler_book=book),
        verdicts,
    )


def basis_for_report(verdict: RulerVerdict | None) -> dict[str, Any] | None:
    if verdict is None:
        return None
    return verdict.basis


def correct_reading(reading: float, correction_mm: float) -> float:
    """统一的净宽换算：真值/净宽 = 读数 + 带符号校尺差。"""
    return round(float(reading) + float(correction_mm), 9)


apply_reading_correction = correct_reading
calibrated_reading = correct_reading
calibrate_reading = correct_reading
net_width = correct_reading
correct_net_width = correct_reading


def effective_correction(
    rows: Iterable[Any],
    ruler_id: str,
    day: int,
    cutoff: int,
    *,
    raw_reading: float | None = None,
    period: Any = None,
) -> RulerVerdict:
    if isinstance(rows, RulerBook):
        book = rows.at(cutoff) if cutoff is not None else rows
    else:
        book = RulerBook.build(rows, cutoff)
    return book.resolve(ruler_id, day, raw_reading, period=period)


resolve_correction = effective_correction
resolve_ruler_correction = effective_correction
calibration_for = effective_correction
ruler_calibration_for = effective_correction


def correction_for(*args, **kwargs) -> float | None:
    verdict = effective_correction(*args, **kwargs)
    return verdict.correction_mm if verdict.status == STATUS_OK else None


def corrected_value(*args, **kwargs) -> float | None:
    verdict = effective_correction(*args, **kwargs)
    return verdict.corrected_reading if verdict.status == STATUS_OK else None


# Descriptive aliases used by different parts of the handover vocabulary.
RulerCorrectionBook = RulerBook
CalibrationBook = RulerBook
RulerRegistry = RulerBook
CalibrationRegistry = RulerBook
RulerService = RulerBook
CalibrationService = RulerBook
RulerCorrection = CalibrationRecord
Calibration = CalibrationRecord
apply_ruler_corrections = apply_book
