from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


CLASS_NAMES = ["Healthy", "Degraded", "Damaged"]


@dataclass
class SegmentState:
    id: int
    true_state: int
    belief: list[float]          # [P(Healthy), P(Degraded), P(Damaged)]
    map_state: int               # argmax(belief)
    map_state_name: str
    entropy: float

    @classmethod
    def build(
        cls,
        segment_id: int,
        true_state: int,
        belief: list[float],
        map_state: int,
        entropy: float,
    ) -> "SegmentState":
        return cls(
            id=segment_id,
            true_state=true_state,
            belief=belief,
            map_state=map_state,
            map_state_name=CLASS_NAMES[map_state],
            entropy=entropy,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TwinState:
    tick: int
    timestamp: str               # ISO-8601
    train_segment: int           # segment the train is currently on
    commanded_speed_fps: float
    alert: str                   # "CLEAR" | "WARNING – ..." | "DANGER – ..."
    segments: list[SegmentState] = field(default_factory=list)

    @classmethod
    def build(
        cls,
        tick: int,
        train_segment: int,
        commanded_speed_fps: float,
        alert: str,
        segments: list[SegmentState],
    ) -> "TwinState":
        return cls(
            tick=tick,
            timestamp=datetime.now(timezone.utc).isoformat(),
            train_segment=train_segment,
            commanded_speed_fps=commanded_speed_fps,
            alert=alert,
            segments=segments,
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        return d
