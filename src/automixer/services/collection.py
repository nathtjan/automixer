from typing import Optional
from automixer.services.base import ThreadService
from automixer.services.camera import CameraService
from automixer.services.interaction import InteractionService
from automixer.services.mic import MicService
from automixer.services.mixing import MixingService
from automixer.services.ocr import OCRService
from automixer.services.slide import SlideService
from automixer.services.transcription import TranscriptionService


class ServiceCollection:
    def __init__(
        self,
        camera: Optional[CameraService] = None,
        interaction: Optional[InteractionService] = None,
        mic: Optional[MicService] = None,
        mixing: Optional[MixingService] = None,
        ocr: Optional[OCRService] = None,
        slide: Optional[SlideService] = None,
        transcription: Optional[TranscriptionService] = None,
    ):
        self.camera = camera
        self.interaction = interaction
        self.mic = mic
        self.mixing = mixing
        self.ocr = ocr
        self.slide = slide
        self.transcription = transcription
        self.services = [
            camera,
            interaction,
            mic,
            mixing,
            ocr,
            slide,
            transcription,
        ]
        # Filter out None services
        self.services = [s for s in self.services if s is not None]

    def start(self):
        for service in self.services:
            if (isinstance(service, ThreadService)):
                service.start()

    def stop(self):
        for service in self.services:
            if (isinstance(service, ThreadService)):
                service.stop()

    def step(self):
        for service in self.services:
            service.step()


__all__ = ["ServiceCollection"]
