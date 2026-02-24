from enum import Enum
from typing import Any
import bubus


class BaseEvent(bubus.BaseEvent):
    pass  # allow future modifications


class SceneType(Enum):
    SLIDE = "slide"
    CAMERA = "camera"
    OTHER = "other"


class CameraFrameEvent(BaseEvent):
    frame: Any


class SlideChangeEvent(BaseEvent):
    slide: Any
    previous_slide: Any


class SlideOCREvent(BaseEvent):
    slide: Any
    ocr_result: Any


class AudioSegmentEvent(BaseEvent):
    segment: Any
    samplerate: int


class TranscriptionEvent(BaseEvent):
    text: str


class MixingResultEvent(BaseEvent):
    scene_type: SceneType


class ProgramChangeEvent(BaseEvent):
    scene_type: SceneType
    scene_name: str


__all__ = [
    "BaseEvent",
    "SceneType",
    "CameraFrameEvent",
    "SlideChangeEvent",
    "SlideOCREvent",
    "AudioSegmentEvent",
    "TranscriptionEvent",
    "MixingResultEvent",
    "ProgramChangeEvent",
]
