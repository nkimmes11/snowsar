"""Core domain types for SnowSAR."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum, IntEnum, auto

from shapely.geometry import box
from shapely.geometry.base import BaseGeometry


class Backend(Enum):
    """Data processing backend."""

    GEE = auto()
    LOCAL = auto()


class AlgorithmID(Enum):
    """Identifiers for available retrieval algorithms."""

    LIEVENS = "lievens"
    ML = "ml"
    DPRSE = "dprse"
    INSAR = "insar"


class QualityFlag(IntEnum):
    """Per-pixel quality flags for retrieval outputs.

    Values defined per PRD Section 7.3.
    """

    VALID = 0
    WET_SNOW = 1
    INSUFFICIENT_SAR = 2
    HIGH_FOREST = 3
    LOW_COHERENCE = 4
    OUTSIDE_RANGE = 5


class SnowClass(Enum):
    """Sturm et al. (1995) snow classification for density modeling."""

    ALPINE = "alpine"
    MARITIME = "maritime"
    PRAIRIE = "prairie"
    TUNDRA = "tundra"
    TAIGA = "taiga"
    EPHEMERAL = "ephemeral"


@dataclass(frozen=True)
class AOI:
    """Area of interest for a retrieval job."""

    geometry: BaseGeometry
    crs: str = "EPSG:4326"

    @classmethod
    def from_bbox(cls, west: float, south: float, east: float, north: float) -> AOI:
        """Create an AOI from a bounding box (lon/lat)."""
        return cls(geometry=box(west, south, east, north))

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return self.geometry.bounds  # type: ignore[return-value]


@dataclass(frozen=True)
class TemporalRange:
    """Date range for a retrieval job."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            msg = f"start ({self.start}) must be <= end ({self.end})"
            raise ValueError(msg)

    @property
    def days(self) -> int:
        return (self.end - self.start).days


@dataclass(frozen=True)
class SceneMetadata:
    """Metadata for a single SAR scene."""

    scene_id: str
    platform: str
    orbit_number: int
    acquisition_date: date
    relative_orbit: int
    geometry: BaseGeometry


@dataclass(frozen=True)
class JobParameters:
    """Complete parameter set for a retrieval job."""

    aoi: AOI
    temporal_range: TemporalRange
    algorithms: list[AlgorithmID]
    backend: Backend = Backend.GEE
    resolution_m: int = 100
    algorithm_params: dict[str, object] = field(default_factory=dict)
