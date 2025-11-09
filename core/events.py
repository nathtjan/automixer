from dataclasses import dataclass
from typing import Any, Tuple, Dict


@dataclass
class CameraFrameEvent:
    frame: Any
    timestamp: float


@dataclass
class SlideTextEvent:
    text: str
    bbox: Tuple[int, int, int, int] | None
    timestamp: float


@dataclass
class AudioChunkEvent:
    chunk: Any
    timestamp: float


@dataclass
class TranscriptionEvent:
    text: str
    timestamp: float


@dataclass
class RougeScoreEvent:
    score: float
    details: Dict[str, float]
    timestamp: float


@dataclass
class SceneChangeRequest:
    scene_name: str
    reason: str
    timestamp: float


@dataclass
class ChangeDetectedEvent:
    """Published when a visual change (slide change) is detected."""
    timestamp: float

