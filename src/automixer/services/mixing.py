from abc import ABC, abstractmethod
import time
from logging import getLogger
from automixer.core.events import (
    MixingResultEvent,
    SceneType,
    Slide2CamScoreEvent,
    SlideChangeEvent,
    SlideOCREvent,
    ProgramChangeEvent,
    TranscriptionEvent,
    TranscriptionStateEvent
)
from automixer.services.base import BaseService, autoregister
from automixer.utils.text import lcs, lcs_1gram
from automixer.core.bus import EventBus


logger = getLogger(__name__)


class BaseSlide2CamScorer(ABC):
    @abstractmethod
    def score(self, slide_text: str, transcription: str) -> float:
        """Calculate a score indicating how well the transcription matches the slide text."""


class ROUGELSlide2CamScorer(BaseSlide2CamScorer):
    def score(self, slide_text: str, transcription: str) -> float:
        lcs_length, _ = lcs(slide_text, transcription)
        rouge_l = lcs_length / len(slide_text)
        return rouge_l


class ROUGE1GramSlide2CamScorer(BaseSlide2CamScorer):
    def __init__(self, tolerance: int = 3):
        self.tolerance = tolerance

    def score(self, slide_text: str, transcription: str) -> float:
        lcs_length, lcs_result = lcs_1gram(
            slide_text.split(),
            transcription.split(),
            self.tolerance
        )
        rouge_1gram = len(" ".join(lcs_result)) / len(slide_text)
        return rouge_1gram


class WeightedAverageSlide2CamScorer(BaseSlide2CamScorer):
    def __init__(
        self,
        weight_scorer_set: list[dict],
    ):
        self.weight_scorer_set = weight_scorer_set

    def score(self, slide_text: str, transcription: str) -> float:
        """Calculate weighted average score from multiple scorers."""
        total_score = 0.0
        for item in self.weight_scorer_set:
            weight = item["weight"]
            scorer = item["scorer"]
            score = scorer.score(slide_text, transcription)
            total_score += weight * score
        total_weight = sum(item["weight"] for item in self.weight_scorer_set)
        return total_score / total_weight


class BaseSlide2CamJury(ABC):
    @abstractmethod
    def decide(self, score_sequence: list[float]) -> bool:
        """Decide whether to switch to camera based on the given score sequence."""
        pass


class ThresholdSlide2CamJury(BaseSlide2CamJury):
    def __init__(self, threshold: float):
        self.threshold = threshold

    def decide(self, score_sequence: list[float]) -> bool:
        """Decide to switch to camera if the score has been above the threshold."""
        latest_score = score_sequence[-1] if score_sequence else 0.0
        return latest_score >= self.threshold


class TotalVariationThresholdSlide2CamJury(BaseSlide2CamJury):
    """
    Decide to switch to camera if the total variation of the score sequence is less than a threshold.
    """
    def __init__(self, threshold: float, length: int = 0):
        """Length of zero means uses all available scores."""
        self.threshold = threshold
        self.length = length

    def decide(self, score_sequence: list[float]) -> bool:
        if (self.length == 0):
            length = len(score_sequence)
        else:
            length = self.length
        if len(score_sequence) < length:
            return False
        # Calculate total variation of the last `length` scores
        total_variation = sum(
            abs(score_sequence[i] - score_sequence[i - 1])
            for i in range(-1, -length, -1)
        )
        return total_variation <= self.threshold


class AndSlide2CamJury(BaseSlide2CamJury):
    def __init__(self, juries: list[BaseSlide2CamJury]):
        self.juries = juries

    def decide(self, score_sequence: list[float]) -> bool:
        return all(jury.decide(score_sequence) for jury in self.juries)


class OrSlide2CamJury(BaseSlide2CamJury):
    def __init__(self, juries: list[BaseSlide2CamJury]):
        self.juries = juries

    def decide(self, score_sequence: list[float]) -> bool:
        return any(jury.decide(score_sequence) for jury in self.juries)


class MixingService(BaseService):
    def __init__(
        self,
        bus: EventBus,
        slide2cam_delay: float,
        slide2cam_scorer: BaseSlide2CamScorer,
        slide2cam_jury: BaseSlide2CamJury,
    ):
        super().__init__(bus)
        self.slide_text = None
        self.transcription = None
        self.slide2cam_delay = slide2cam_delay
        self.slide2cam_scorer = slide2cam_scorer
        self.slide2cam_jury = slide2cam_jury
        self.score_sequence = []
        self._threshold_crossed_at = None
        self._last_score = 0.0

    @autoregister
    def on_slide_change(self, event: SlideChangeEvent):
        self.bus.dispatch(MixingResultEvent(scene_type=SceneType.SLIDE))

    @autoregister
    def on_slide_ocr(self, event: SlideOCREvent):
        ocr_result = event.ocr_result
        slide_text = " ".join([elem[1] for elem in ocr_result]).lower()
        self.slide_text = slide_text
        logger.debug(f"Updated slide text: {self.slide_text}")
        self.update_slide2cam_score()

    @autoregister
    def on_transcription(self, event: TranscriptionEvent):
        text = event.text
        if self.transcription is None:
            self.transcription = text.lower()
            logger.debug(f"Initialized transcription: {self.transcription}")
        else:
            self.transcription = self.transcription.rstrip("...")
            self.transcription += " " + text.lower()
            logger.debug(f"Updated transcription: {self.transcription}")
        self.bus.dispatch(TranscriptionStateEvent(text=self.transcription))
        self.update_slide2cam_score()

    @autoregister
    def on_program_change(self, event: ProgramChangeEvent):
        if event.scene_type is SceneType.CAMERA:
            self.slide_text = None
            self.transcription = None
            self.score_sequence = []
            self._threshold_crossed_at = None

    def calculate_slide2cam_score(self):
        if not self.slide_text or not self.transcription:
            return 0
        score = self.slide2cam_scorer.score(self.slide_text, self.transcription)
        logger.debug(f"Calculated slide2cam score: {score}")
        return score

    def update_slide2cam_score(self):
        self._last_score = self.calculate_slide2cam_score()
        self.score_sequence.append(self._last_score)
        self.bus.dispatch(Slide2CamScoreEvent(score=self._last_score))
        if not self.slide2cam_jury.decide(self.score_sequence):
            self._threshold_crossed_at = None
            return
        if self._threshold_crossed_at is None:
            self._threshold_crossed_at = time.time()
            return

    async def step(self):
        if self._threshold_crossed_at is None:
            return
        if time.time() - self._threshold_crossed_at > self.slide2cam_delay:
            self.bus.dispatch(MixingResultEvent(scene_type=SceneType.CAMERA))


__all__ = [
    "BaseSlide2CamScorer",
    "ROUGELSlide2CamScorer",
    "ROUGE1GramSlide2CamScorer",
    "WeightedAverageSlide2CamScorer",
    "BaseSlide2CamJury",
    "ThresholdSlide2CamJury",
    "TotalVariationThresholdSlide2CamJury",
    "AndSlide2CamJury",
    "OrSlide2CamJury",
    "MixingService",
]
