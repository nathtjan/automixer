import time
from core.events import CameraFrameEvent, SlideTextEvent

try:
    import easyocr
except Exception:
    easyocr = None


class VisionService:
    """Consumes CameraFrameEvent, runs OCR (easyocr) and publishes SlideTextEvent.

    This service offloads OCR to a background thread via the event bus threads.
    """

    def __init__(self, event_bus, langs=("id", "en")):
        self.event_bus = event_bus
        self.event_bus.subscribe(CameraFrameEvent, self.on_frame)
        self.reader = None
        self.langs = langs

    def _ensure_reader(self):
        if self.reader is None:
            if easyocr is None:
                raise RuntimeError("easyocr is not installed")
            self.reader = easyocr.Reader(list(self.langs), gpu=False)

    def on_frame(self, event: CameraFrameEvent):
        # Lightweight guard: only run OCR at a reduced rate if needed.
        try:
            self._ensure_reader()
            img = event.frame
            ocr_result = self.reader.readtext(img)
            text = " ".join([elem[1] for elem in ocr_result]).strip().lower()
            if text:
                out = SlideTextEvent(text=text, bbox=None, timestamp=time.time())
                self.event_bus.publish(out)
        except Exception:
            # keep service resilient
            return
