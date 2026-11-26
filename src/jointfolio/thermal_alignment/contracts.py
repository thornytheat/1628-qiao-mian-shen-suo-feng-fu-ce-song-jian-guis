from dataclasses import dataclass, field

from ..joint_register.contracts import Observation


@dataclass(frozen=True)
class Signal:
    record: Observation
    vector: tuple[float, ...]
    normalized: tuple[float, ...]
    missing: tuple[str, ...]
    reference: str
    fills: dict[str, float] | None = field(default=None, compare=False)
    centers: tuple[float, ...] | None = field(default=None, compare=False)
    scales: tuple[float, ...] | None = field(default=None, compare=False)


@dataclass(frozen=True)
class Scale:
    fills: dict[str, float]
    centers: tuple[float, ...]
    slopes: tuple[float, ...]
    support: int


@dataclass(frozen=True)
class FeatureBank:
    as_of: int
    global_scale: Scale
    group_scales: dict[str, Scale]
    population: dict[str, int]
