import asyncio
from logging import getLogger
from queue import Queue
from easyocr import Reader
from automixer.core.events import (
    ProgramChangeEvent,
    SlideChangeEvent,
    SlideOCREvent,
    ValidCameraFrameEvent,
    SceneType
)
from automixer.services.base import ThreadService, autoregister


logger = getLogger(__name__)


class OCRService(ThreadService):
    def __init__(self, bus, reader: Reader, expect_frame_timeout: float = 5.0):
        super().__init__(bus)
        self.reader = reader
        self.expect_frame_timeout = expect_frame_timeout
        self._pending_frame_queue = Queue()
        self._ocr_result_queue = Queue()


    async def up(self):
        await super().up()
        self.start()

    def run(self):
        while not self.should_stop():
            if self._pending_frame_queue.empty():
                continue
            frame = self._pending_frame_queue.get()
            if frame is None:
                continue
            ocr_result = self.reader.readtext(frame)
            self._ocr_result_queue.put((frame, ocr_result))

    def stop(self):
        super().stop()
        # Empty all queue
        while not self._pending_frame_queue.empty():
            self._pending_frame_queue.get()
        while not self._ocr_result_queue.empty():
            self._ocr_result_queue.get()

    @autoregister
    async def on_program_change(self, event: ProgramChangeEvent):
        if event.scene_type == SceneType.SLIDE:
            asyncio.create_task(self._handle_program_change(event))

    async def _handle_program_change(self, event: ProgramChangeEvent):
        try:
            cam_frame_event = await self.bus.expect(ValidCameraFrameEvent, timeout=self.expect_frame_timeout)
        except asyncio.TimeoutError:
            logger.warning("No valid camera frame received within timeout after program change.")
            return
        self._pending_frame_queue.put(cam_frame_event.frame)

    @autoregister
    async def on_slide_change(self, event: SlideChangeEvent):
        self._pending_frame_queue.put(event.slide)

    async def step(self):
        while not self._ocr_result_queue.empty():
            frame, ocr_result = self._ocr_result_queue.get()
            logger.debug(f"OCR result for slide: {ocr_result}")
            self.bus.dispatch(SlideOCREvent(slide=frame, ocr_result=ocr_result))


__all__ = ["OCRService"]
