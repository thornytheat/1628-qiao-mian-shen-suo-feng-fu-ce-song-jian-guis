from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Observation:
    case_id: str
    group: str
    day: int
    arrived: int
    revision: int
    clock: int
    reported: dict[str, float | None]
    ruler_id: str | None = None
    raw_reading: float | None = None
    ruler_status: str = "NOT_REQUIRED"
    ruler_reason: str = ""
    ruler_basis: dict[str, Any] | None = None
    ruler_period: str | None = None


@dataclass(frozen=True)
class Outcome:
    case_id: str
    available: int
    value: float
    occurred: bool


@dataclass(frozen=True)
class Rejection:
    code: str
    stream: str
    case_id: str
    detail: str
    occurrences: int = 1


@dataclass(frozen=True)
class Intake:
    observations: tuple[Observation, ...]
    outcomes: tuple[Outcome, ...]
    rejections: tuple[Rejection, ...]
    source_counts: dict[str, int]
    calibrations: tuple[Any, ...] = ()
    ruler_book: Any = None
