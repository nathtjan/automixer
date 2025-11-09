import time
from concurrent.futures import ThreadPoolExecutor
from core.events import SlideTextEvent, TranscriptionEvent, RougeScoreEvent
from metric import lcs, lcs_1gram


class RougeService:
    def __init__(self, event_bus, rouge1_weight=0.9, rougel_weight=0.1, rouge_threshold=0.8):
        self.event_bus = event_bus
        self.rouge1_weight = rouge1_weight
        self.rougel_weight = rougel_weight
        self.rouge_threshold = rouge_threshold
        self.slide_text = None
        self.transcription = None
        self.executor = ThreadPoolExecutor(max_workers=2)

        self.event_bus.subscribe(SlideTextEvent, self._on_slide)
        self.event_bus.subscribe(TranscriptionEvent, self._on_transcription)

    def _on_slide(self, event: SlideTextEvent):
        self.slide_text = event.text
        self._maybe_compute()

    def _on_transcription(self, event: TranscriptionEvent):
        self.transcription = event.text
        self._maybe_compute()

    def _maybe_compute(self):
        if not self.slide_text or not self.transcription:
            return
        # offload heavy compute
        self.executor.submit(self._compute_and_publish)

    def _compute_and_publish(self):
        try:
            s = self.slide_text
            t = self.transcription
            # 1-gram LCS
            _, lcs_result = lcs_1gram(s.split(), t.split(), 3)
            rouge_1gram = len(" ".join(lcs_result)) / max(1, len(s))
            lcs_length, _ = lcs(s, t)
            rouge_l = lcs_length / max(1, len(s))
            score = self.rouge1_weight * rouge_1gram + self.rougel_weight * rouge_l
            evt = RougeScoreEvent(score=score, details={"rouge1": rouge_1gram, "rougel": rouge_l}, timestamp=time.time())
            self.event_bus.publish(evt)
        except Exception:
            return
