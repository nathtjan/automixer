from typing import List, Optional, ClassVar, Literal, Union, Annotated
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
    def filter_global_kwargs(cls, kwargs: dict) -> dict:
        return kwargs

    @classmethod
    def instantiate(cls, *args, **kwargs) -> object:
        return cls.get_class()(*args, **kwargs)


class InstantiableThirdPartyClassConfig(InstantiableClassConfig):
    model_config = {
        "extra": "allow"
    }

    @classmethod
    def filter_kwargs(cls, kwargs: dict) -> dict:
        # Assume all kwargs are valid
        return kwargs

    @classmethod
    def filter_global_kwargs(cls, kwargs: dict) -> dict:
        # Drop all global kwargs
        return {}


class CameraConfig(InstantiableThirdPartyClassConfig):
    _class: ClassVar[type] = cv2.VideoCapture


class MicConfig(InstantiableThirdPartyClassConfig):
    _class: ClassVar[type] = sd.InputStream


class OBSInteractorConfig(InstantiableClassConfig):
    software: Literal["obs"]
    host: str
    port: str
    password: Optional[SecretStr] = None
    _class: ClassVar[type] = interactors.OBSInteractor

    @classmethod
    def instantiate(cls, *args, **kwargs) -> object:
        # Override to handle SecretStr for password
        if "password" in kwargs and isinstance(kwargs["password"], SecretStr):
            kwargs["password"] = kwargs["password"].get_secret_value()
        return cls.get_class()(*args, **kwargs)


class OCRReaderConfig(InstantiableThirdPartyClassConfig):
    _class: ClassVar[type] = easyocr.Reader


class OpenAIClientConfig(InstantiableThirdPartyClassConfig):
    _class: ClassVar[type] = OpenAI


class OpenAITranscriberConfig(InstantiableClassConfig):
    client: OpenAIClientConfig
    model: str
    language: Optional[str] = None
    _class: ClassVar[type] = OpenAITranscriber

    @classmethod
    def filter_kwargs(cls, kwargs: dict) -> dict:
        # Allow language param
        return {
            "client": kwargs["client"].instantiate(),
            "model": kwargs["model"],
            "language": kwargs.get("language"),
        }


class BaseNotifierConfig(InstantiableClassConfig):
    pass


class MQTTNotifierConfig(BaseNotifierConfig):
    notifier_type: Literal["mqtt"] = "mqtt"
    host: str
    topic: str
    port: int = 1883
    qos: int = 0
    retain: bool = False
    keepalive: int = 60
    use_tls: bool = False
    mqtt_version: int = 5
    client_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[SecretStr] = None
    _class: ClassVar[type] = services.MQTTNotifier

    @classmethod
    def instantiate(cls, *args, **kwargs) -> object:
        if "password" in kwargs and isinstance(kwargs["password"], SecretStr):
            kwargs["password"] = kwargs["password"].get_secret_value()
        return cls.get_class()(*args, **kwargs)


class BaseServiceConfig(InstantiableClassConfig):
    pass  # For future common attributes


class CameraServiceConfig(BaseServiceConfig):
    service_type: Literal["camera"] = "camera"
    camera: CameraConfig
    read_delay: Optional[float] = 0.1
    _class: ClassVar[type] = services.CameraService


class InteractionServiceConfig(BaseServiceConfig):
    service_type: Literal["interaction"] = "interaction"
    interactor: Union[OBSInteractorConfig] = Field(discriminator='software')  # Can be extended to support other interactors in the future
    slide_scenenames: List[str]
    default_slide_scenename: str
    cam_scenename: str
    program_check_delay: float = 0.1
    _class: ClassVar[type] = services.InteractionService


class MicServiceConfig(BaseServiceConfig):
    service_type: Literal["mic"] = "mic"
    input_stream: MicConfig
    read_frames: int
    _class: ClassVar[type] = services.MicService


class MixingServiceConfig(BaseServiceConfig):
    service_type: Literal["mixing"] = "mixing"
    rouge_1gram_weight: float
    rouge_l_weight: float
    slide2cam_threshold: float
    slide2cam_delay: float
    _class: ClassVar[type] = services.MixingService


class OCRServiceConfig(BaseServiceConfig):
    service_type: Literal["ocr"] = "ocr"
    reader: OCRReaderConfig
    expect_frame_timeout: float = 5.0
    _class: ClassVar[type] = services.OCRService


class SlideServiceConfig(BaseServiceConfig):
    service_type: Literal["slide"] = "slide"
    diff_threshold: float
    edge_threshold: float
    full_black_threshold_mean: float
    full_black_threshold_std: float
    _class: ClassVar[type] = services.SlideService


class TranscriptionServiceConfig(BaseServiceConfig):
    service_type: Literal["transcription"] = "transcription"
    transcriber: OpenAITranscriberConfig
    run_delay: float = 0.1
    _class: ClassVar[type] = services.TranscriptionService


class NotificationServiceConfig(BaseServiceConfig):
    service_type: Literal["notification"] = "notification"
    notifier: Annotated[
        Union[MQTTNotifierConfig],
        Field(discriminator="notifier_type")
    ]
    include_event_types: Optional[List[str]] = None
    exclude_event_types: Optional[List[str]] = None
    _class: ClassVar[type] = services.NotificationService


class AutomixerConfig(InstantiableClassConfig):
    services: List[Annotated[
        Union[
            CameraServiceConfig,
            InteractionServiceConfig,
            MicServiceConfig,
            MixingServiceConfig,
            OCRServiceConfig,
            SlideServiceConfig,
            TranscriptionServiceConfig,
            NotificationServiceConfig,
        ],
        Field(discriminator="service_type")
    ]]
    _class: ClassVar[type] = Automixer


__all__ = [
    "InstantiableClassConfig",
    "CameraConfig",
    "MicConfig",
    "OBSInteractorConfig",
    "OCRReaderConfig",
    "OpenAIClientConfig",
    "OpenAITranscriberConfig",
    "BaseNotifierConfig",
    "MQTTNotifierConfig",
    "BaseServiceConfig",
    "CameraServiceConfig",
    "InteractionServiceConfig",
    "MicServiceConfig",
    "MixingServiceConfig",
    "OCRServiceConfig",
    "SlideServiceConfig",
    "TranscriptionServiceConfig",
    "NotificationServiceConfig",
    "AutomixerConfig",
    "preprocess_config",
]
