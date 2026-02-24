from typing import List, Optional, ClassVar, Literal, Union
import inspect

import cv2
import easyocr
from openai import OpenAI
from pydantic import SecretStr, BaseModel, Field
import sounddevice as sd

from automixer.services.transcription import OpenAITranscriber
from automixer import services, interactors, Automixer


class InstantiableClassConfig(BaseModel):
    _class: ClassVar[type]

    @classmethod
    def get_class(cls) -> type:
        return cls._class

    @classmethod
    def filter_kwargs(cls, kwargs: dict) -> dict:
        # Filter kwargs to only those accepted by the class constructor
        sig = inspect.signature(cls.get_class().__init__)
        param_names = set(sig.parameters.keys()) - {"self"}
        return {k: v for k, v in kwargs.items() if k in param_names}

    @classmethod
    def instantiate(cls, *args, **kwargs) -> object:
        return cls.get_class()(*args, **kwargs)


class CameraConfig(InstantiableClassConfig):
    index: int
    _class: ClassVar[type] = cv2.VideoCapture

    @classmethod
    def filter_kwargs(cls, kwargs: dict) -> dict:
        return {"index": kwargs["index"]}  # cv2.VideoCapture only accepts 'index' as an argument


class MicConfig(InstantiableClassConfig):
    device: int
    channels: int
    samplerate: int
    blocksize: int = 1024
    _class: ClassVar[type] = sd.InputStream


class OBSInteractorConfig(InstantiableClassConfig):
    software: Literal["obs"]
    host: str
    port: str
    password: Optional[SecretStr] = None
    _class: ClassVar[type] = interactors.OBSInteractor


class OCRReaderConfig(InstantiableClassConfig):
    lang_list: List[str]
    _class: ClassVar[type] = easyocr.Reader


class OpenAIClientConfig(InstantiableClassConfig):
    _class: ClassVar[type] = OpenAI


class OpenAITranscriberConfig(InstantiableClassConfig):
    client: OpenAIClientConfig
    model: str
    language: Optional[str] = None
    _class: ClassVar[type] = OpenAITranscriber


class BaseServiceConfig(InstantiableClassConfig):
    pass  # For future common attributes


class CameraServiceConfig(BaseServiceConfig):
    camera: CameraConfig
    read_delay: Optional[float] = 0.1
    _class: ClassVar[type] = services.CameraService


class InteractionServiceConfig(BaseServiceConfig):
    interactor: Union[OBSInteractorConfig] = Field(discriminator='software')  # Can be extended to support other interactors in the future
    slide_scenenames: List[str]
    default_slide_scenename: str
    cam_scenename: str
    program_check_delay: float = 0.1
    _class: ClassVar[type] = services.InteractionService


class MicServiceConfig(BaseServiceConfig):
    input_stream: MicConfig
    read_frames: int
    _class: ClassVar[type] = services.MicService


class MixingServiceConfig(BaseServiceConfig):
    rouge_1gram_weight: float
    rouge_l_weight: float
    slide2cam_threshold: float
    slide2cam_delay: float
    _class: ClassVar[type] = services.MixingService


class OCRServiceConfig(BaseServiceConfig):
    reader: OCRReaderConfig
    _class: ClassVar[type] = services.OCRService


class SlideServiceConfig(BaseServiceConfig):
    diff_threshold: float
    edge_threshold: float
    full_black_threshold_mean: float
    full_black_threshold_std: float
    _class: ClassVar[type] = services.SlideService


class TranscriptionServiceConfig(BaseServiceConfig):
    transcriber: OpenAITranscriberConfig
    run_delay: float = 0.1
    _class: ClassVar[type] = services.TranscriptionService


class ServiceCollectionConfig(InstantiableClassConfig):
    camera: CameraServiceConfig
    interaction: InteractionServiceConfig
    mic: MicServiceConfig
    mixing: MixingServiceConfig
    ocr: OCRServiceConfig
    slide: SlideServiceConfig
    transcription: TranscriptionServiceConfig
    _class: ClassVar[type] = services.ServiceCollection


class AutomixerConfig(InstantiableClassConfig):
    service_collection: ServiceCollectionConfig
    _class: ClassVar[type] = Automixer


__all__ = [
    "InstantiableClassConfig",
    "CameraConfig",
    "MicConfig",
    "OBSInteractorConfig",
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
