from pydantic import BaseModel


class SegmentStateResponse(BaseModel):
    id: int
    true_state: int
    belief: list[float]          # [P(Healthy), P(Degraded), P(Damaged)]
    map_state: int               # 0=Healthy 1=Degraded 2=Damaged
    map_state_name: str
    entropy: float


class TwinStateResponse(BaseModel):
    tick: int
    timestamp: str               # ISO-8601
    train_segment: int
    commanded_speed_fps: float
    alert: str                   # "CLEAR" | "WARNING – ..." | "DANGER – ..."
    segments: list[SegmentStateResponse]


class CorrectionRequest(BaseModel):
    segment_id: int
    state: int                   # 0=Healthy 1=Degraded 2=Damaged

class TrackConfigRequest(BaseModel):
    track_config: list[int]           # e.g. [0, 1, 2, 1, 0] — one entry per segment
    segment_length_cm: float | None = None  # optional — keeps current value if omitted


class TrackConfigResponse(BaseModel):
    track_config: list[int]
    segment_length_cm: float
    num_segments: int


def twin_state_to_response(state) -> TwinStateResponse:
    """Convert a TwinState dataclass to its Pydantic response model."""
    return TwinStateResponse(
        tick=state.tick,
        timestamp=state.timestamp,
        train_segment=state.train_segment,
        commanded_speed_fps=state.commanded_speed_fps,
        alert=state.alert,
        segments=[
            SegmentStateResponse(
                id=s.id,
                true_state=s.true_state,
                belief=s.belief,
                map_state=s.map_state,
                map_state_name=s.map_state_name,
                entropy=s.entropy,
            )
            for s in state.segments
        ],
    )
