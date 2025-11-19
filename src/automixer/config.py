from typing import List, Optional, ClassVar

import cv2
import easyocr
from openai import OpenAI
from pydantic import SecretStr, SerializationInfo, field_serializer
from pydantic.dataclasses import dataclass
import sounddevice as sd

from automixer.services.transcription import OpenAITranscriber
from automixer import services, interactors, Automixer, EventBus


@dataclass
class InstatiableClassConfig:
    _class: ClassVar[type]

    @classmethod
    def get_class(cls) -> type:
        return cls._class


@dataclass
class CameraConfig(InstatiableClassConfig):
    id: int
    _class: ClassVar[type] = cv2.VideoCapture


@dataclass
class MicConfig(InstatiableClassConfig):
    samplerate: int
    channels: int
    _class: ClassVar[type] = sd.InputStream


@dataclass
class OBSCredentialConfig(InstatiableClassConfig):
    host: str
    port: str
    password: SecretStr
    _class: ClassVar[type] = None

    @field_serializer("password")
    def serialize_password(self, password: SecretStr, info: SerializationInfo) -> str:
        if info.context.get("!!!serialize_secrets!!!", False):
            return password.get_secret_value()
        return str(password)


@dataclass
class InteractorConfig(InstatiableClassConfig):
    software: str
    credentials: OBSCredentialConfig

    def get_class(self) -> type:
        return interactors.utils.get_interactor_class(self.software)


@dataclass
class OCRReaderConfig(InstatiableClassConfig):
    _class: ClassVar[type] = easyocr.Reader


@dataclass
class OpenAIClientConfig(InstatiableClassConfig):
    _class: ClassVar[type] = OpenAI


@dataclass
class OpenAITranscriberConfig(InstatiableClassConfig):
    client: OpenAIClientConfig
    model: str
    language: Optional[str] = None
    _class: ClassVar[type] = OpenAITranscriber


@dataclass
class BaseServiceConfig(InstatiableClassConfig):
    pass  # For future common attributes


@dataclass
class CameraServiceConfig(BaseServiceConfig):
    camera: CameraConfig
    _class: ClassVar[type] = services.CameraService


@dataclass
class InteractionServiceConfig(BaseServiceConfig):
    interactor: InteractorConfig
    slide_scenenames: List[str]
    default_slide_scenename: str
    cam_scenename: str
    program_check_delay: float = 0.1
    _class: ClassVar[type] = services.InteractionService


@dataclass
class MicServiceConfig(BaseServiceConfig):
    input_stream: MicConfig
    read_frames: int
    _class: ClassVar[type] = services.MicService


@dataclass
class MixingServiceConfig(BaseServiceConfig):
    rouge_1gram_weight: float
    rouge_l_weight: float
    slide2cam_threshold: float
    slide2cam_delay: float
    _class: ClassVar[type] = services.MixingService


@dataclass
class OCRServiceConfig(BaseServiceConfig):
    reader: OCRReaderConfig
    _class: ClassVar[type] = services.OCRService


@dataclass
class SlideServiceConfig(BaseServiceConfig):
    diff_threshold: float
    edge_threshold: float
    full_black_threshold_mean: float
    full_black_threshold_std: float
    _class: ClassVar[type] = services.SlideService


@dataclass
class TranscriptionServiceConfig(BaseServiceConfig):
    transcriber: OpenAITranscriberConfig
    run_delay: float = 0.1
    _class: ClassVar[type] = services.TranscriptionService


@dataclass
class ServiceCollectionConfig(InstatiableClassConfig):
    camera: CameraServiceConfig
    interaction: InteractionServiceConfig
    mic: MicServiceConfig
    mixing: MixingServiceConfig
    ocr: OCRServiceConfig
    slide: SlideServiceConfig
    transcription: TranscriptionServiceConfig
    _class: ClassVar[type] = services.ServiceCollection


@dataclass
class AutomixerConfig(InstatiableClassConfig):
    service_collection: ServiceCollectionConfig
    _class: ClassVar[type] = Automixer


__all__ = [
    "InstatiableClassConfig",
    "CameraConfig",
    "MicConfig",
    "OBSCredentialConfig",
    "InteractorConfig",
    "OCRReaderConfig",
    "OpenAIClientConfig",
    "OpenAITranscriberConfig",
    "BaseServiceConfig",
    "CameraServiceConfig",
    "InteractionServiceConfig",
    "MicServiceConfig",
    "MixingServiceConfig",
    "OCRServiceConfig",
    "SlideServiceConfig",
    "TranscriptionServiceConfig",
    "ServiceCollectionConfig",
    "AutomixerConfig",
]
