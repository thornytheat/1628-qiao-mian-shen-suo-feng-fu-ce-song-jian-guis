from dataclasses import dataclass, field
from typing import Any


STATUS_UNTRACKED = "NOT_REQUIRED"
STATUS_OK = "APPLIED"
STATUS_MISSING = "MISSING"
STATUS_CONFLICT = "CONFLICT"

REASON_MISSING = "RULER_CORRECTION_MISSING"
REASON_CONFLICT = "RULER_CORRECTION_CONFLICT"
REASON_INVALID = "RULER_CORRECTION_INVALID"
REASON_LATE = "RULER_CORRECTION_NOT_CONFIRMED"

REASON_ALIASES = {
    REASON_MISSING: (
        "RULER_CALIBRATION_MISSING",
        "CALIBRATION_MISSING",
        "RULER_CORRECTION_NOT_CONFIRMED",
    ),
    REASON_CONFLICT: (
        "RULER_CALIBRATION_CONFLICT",
        "CALIBRATION_CONFLICT",
    ),
}


@dataclass(frozen=True)
class CalibrationRecord:
    ruler_id: str
    correction_mm: float
    confirmed_day: int
    day: int | None = None
    start_day: int | None = None
    end_day: int | None = None
    period: str | None = None
    scope: tuple[Any, ...] = ("global",)
    fingerprint: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RulerVerdict:
    status: str
    ruler_id: str | None = None
    reason: str = ""
    correction_mm: float = 0.0
    raw_reading: float | None = None
    corrected_reading: float | None = None
    confirmed_day: int | None = None
    effective_day: int | None = None
    period: str | None = None
    late_records: int = 0
    basis: dict[str, Any] | None = None

    @property
    def allowed(self) -> bool:
        return self.status in {STATUS_OK, STATUS_UNTRACKED}
