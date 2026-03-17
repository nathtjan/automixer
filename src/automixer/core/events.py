from enum import Enum
from typing import Any
import bubus


class BaseEvent(bubus.BaseEvent):
    pass  # allow future modifications

    def serialize(self, **kwargs):
        if ("include" not in kwargs) and hasattr(self, "_SERIALIZE_INCLUDE"):
            kwargs["include"] = self._SERIALIZE_INCLUDE
        if ("exclude" not in kwargs) and hasattr(self, "_SERIALIZE_EXCLUDE"):
            kwargs["exclude"] = self._SERIALIZE_EXCLUDE
        return self.model_dump(**kwargs)


class SceneType(Enum):
    SLIDE = "slide"
    CAMERA = "camera"
    OTHER = "other"


class CameraFrameEvent(BaseEvent):
    _SERIALIZE_INCLUDE = {"frame"}
    frame: Any


class ValidCameraFrameEvent(CameraFrameEvent):
    pass


class SlideChangeEvent(BaseEvent):
    _SERIALIZE_INCLUDE = {"slide", "previous_slide"}
    slide: Any
    previous_slide: Any


class SlideOCREvent(BaseEvent):
    _SERIALIZE_INCLUDE = {"slide", "ocr_result"}
    slide: Any
    ocr_result: Any


class AudioSegmentEvent(BaseEvent):
    _SERIALIZE_INCLUDE = {"segment", "samplerate"}
    segment: Any
    samplerate: int


class TranscriptionEvent(BaseEvent):
    _SERIALIZE_INCLUDE = {"text"}
    text: str


class MixingResultEvent(BaseEvent):
    _SERIALIZE_INCLUDE = {"scene_type"}
    scene_type: SceneType


class ProgramChangeEvent(BaseEvent):
    _SERIALIZE_INCLUDE = {"scene_type", "scene_name"}
    scene_type: SceneType
    scene_name: str


class Slide2CamScoreEvent(BaseEvent):
    _SERIALIZE_INCLUDE = {"score"}
    score: float


class TranscriptionStateEvent(BaseEvent):
    _SERIALIZE_INCLUDE = {"text"}
    text: str


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
    "Slide2CamScoreEvent",
    "TranscriptionStateEvent",
]
