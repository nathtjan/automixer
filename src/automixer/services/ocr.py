from logging import getLogger
from easyocr import Reader
from automixer.core.events import SlideChangeEvent, SlideOCREvent
from automixer.services.base import BaseService, autoregister


logger = getLogger(__name__)


class OCRService(BaseService):
    def __init__(self, bus, reader: Reader):
        super().__init__(bus)
        self.reader = reader

    @autoregister
    def on_slide_change(self, event: SlideChangeEvent):
        slide = event.slide
        ocr_result = self.reader.readtext(slide)
        logger.debug(f"OCR result for slide {slide}: {ocr_result}")
        self.bus.dispatch(SlideOCREvent(slide=slide, ocr_result=ocr_result))


__all__ = ["OCRService"]
