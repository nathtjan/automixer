import time
from logging import getLogger
from automixer.core.events import (
    MixingResultEvent,
    SceneType,
    SlideChangeEvent,
    SlideOCREvent,
    ProgramChangeEvent,
    TranscriptionEvent
)
from automixer.services.base import BaseService, autoregister
from automixer.utils.text import lcs, lcs_1gram
from automixer.core.bus import EventBus


logger = getLogger(__name__)


class MixingService(BaseService):
    def __init__(
        self,
        bus: EventBus,
        rouge_1gram_weight: float,
        rouge_l_weight: float,
        slide2cam_threshold: float,
        slide2cam_delay: float
    ):
        super().__init__(bus)
        self.slide_text = None
        self.transcription = None
        self.rouge_1gram_weight = rouge_1gram_weight
        self.rouge_l_weight = rouge_l_weight
        self.slide2cam_threshold = slide2cam_threshold
        self.slide2cam_delay = slide2cam_delay
        self._threshold_crossed_at = None

    @autoregister
    def on_slide_change(self, event: SlideChangeEvent):
        self.bus.dispatch(MixingResultEvent(scene_type=SceneType.SLIDE))

    @autoregister
    def on_slide_ocr(self, event: SlideOCREvent):
        ocr_result = event.ocr_result
        slide_text = " ".join([elem[1] for elem in ocr_result]).lower()
        self.slide_text = slide_text
        logger.debug(f"Updated slide text: {self.slide_text}")

    @autoregister
    def on_transcription(self, event: TranscriptionEvent):
        text = event.text
        if self.transcription is None:
            self.transcription = text.lower()
            logger.debug(f"Initialized transcription: {self.transcription}")
            return
        self.transcription = self.transcription.rstrip("...")
        self.transcription += " " + text.lower()
        logger.debug(f"Updated transcription: {self.transcription}")

    @autoregister
    def on_program_change(self, event: ProgramChangeEvent):
        if event.scene_type is SceneType.CAMERA:
            self.slide_text = None
            self.transcription = None
            self._threshold_crossed_at = None

    def calculate_slide2cam_score(self):
        if not self.slide_text or not self.transcription:
            return 0
        lcs_length, lcs_result = lcs_1gram(
            self.slide_text.split(),
            self.transcription.split(),
            3
        )
        rouge_1gram = len(" ".join(lcs_result)) / len(self.slide_text)
        lcs_length, lcs_result = lcs(self.slide_text, self.transcription)
        rouge_l = lcs_length / len(self.slide_text)
        rouge_score = (
            self.rouge_1gram_weight * rouge_1gram
            + self.rouge_l_weight * rouge_l
        )
        logger.debug(f"Calculated slide2cam score: {rouge_score}")
        return rouge_score

    def step(self):
        if self.calculate_slide2cam_score() < self.slide2cam_threshold:
            return
        if self._threshold_crossed_at is None:
            self._threshold_crossed_at = time.time()
            return
        if time.time() - self._threshold_crossed_at > self.slide2cam_delay:
            self.bus.dispatch(MixingResultEvent(scene_type=SceneType.CAMERA))


__all__ = ["MixingService"]
