from enum import Enum
from typing import Any, ClassVar
import bubus
from pydantic.main import IncEx


class BaseEvent(bubus.BaseEvent):
    NAME: ClassVar[str | None] = None

    def serialize(self, **kwargs):
        if ("include" not in kwargs) and hasattr(self, "SERIALIZE_INCLUDE"):
            kwargs["include"] = self.SERIALIZE_INCLUDE
        if ("exclude" not in kwargs) and hasattr(self, "SERIALIZE_EXCLUDE"):
            kwargs["exclude"] = self.SERIALIZE_EXCLUDE
        return self.model_dump(**kwargs)

    @classmethod
    def get_name(cls) -> str:
        if cls.NAME is not None:
            return cls.NAME
        else:
            # Convert class name to snake case
            name = cls.__name__
            name = "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")
            # Strip suffix
            if name.endswith("_event"):
                name = name[:-6]
            return name


class SceneType(Enum):
    SLIDE = "slide"
    CAMERA = "camera"
    OTHER = "other"


class CameraFrameEvent(BaseEvent):
    SERIALIZE_INCLUDE: ClassVar[IncEx] = {"frame"}
    frame: Any


class ValidCameraFrameEvent(CameraFrameEvent):
    pass


class SlideChangeEvent(BaseEvent):
    SERIALIZE_INCLUDE: ClassVar[IncEx] = {"slide", "previous_slide"}
    slide: Any
    previous_slide: Any


class SlideOCREvent(BaseEvent):
    SERIALIZE_INCLUDE: ClassVar[IncEx] = {"slide", "ocr_result"}
    slide: Any
    ocr_result: Any


class AudioSegmentEvent(BaseEvent):
    SERIALIZE_INCLUDE: ClassVar[IncEx] = {"segment", "samplerate"}
    segment: Any
    samplerate: int


class TranscriptionEvent(BaseEvent):
    SERIALIZE_INCLUDE: ClassVar[IncEx] = {"text"}
    text: str


class MixingResultEvent(BaseEvent):
    SERIALIZE_INCLUDE: ClassVar[IncEx] = {"scene_type"}
    scene_type: SceneType


class ProgramChangeEvent(BaseEvent):
    SERIALIZE_INCLUDE: ClassVar[IncEx] = {"scene_type", "scene_name"}
    scene_type: SceneType
    scene_name: str


class Slide2CamScoreEvent(BaseEvent):
    SERIALIZE_INCLUDE: ClassVar[IncEx] = {"score"}
    score: float


class TranscriptionStateEvent(BaseEvent):
    SERIALIZE_INCLUDE: ClassVar[IncEx] = {"text"}
    text: str


def _get_all_event_classes() -> list[type[BaseEvent]]:
    event_classes = []

    def _get_subclasses(cls):
        for subclass in cls.__subclasses__():
            event_classes.append(subclass)
            _get_subclasses(subclass)

    _get_subclasses(BaseEvent)
    return event_classes


def get_event_class(name: str) -> type[BaseEvent] | None:
    subclasses = _get_all_event_classes()
    for event_cls in subclasses:
        if event_cls.get_name() == name:
            return event_cls
    return None


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
    "get_event_class",
]
