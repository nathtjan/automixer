from logging import getLogger
from queue import Queue
import time
from automixer.core.events import CameraFrameEvent
from automixer.services.base import ThreadService
import cv2


logger = getLogger(__name__)


class CameraService(ThreadService):
    def __init__(
        self,
        bus,
        camera: cv2.VideoCapture,
        read_delay: float = 0.1
    ):
        super().__init__(bus)
        self.camera = camera
        self.read_delay = read_delay
        self._camera_frame_queue = Queue()

    def run(self):
        while not self.should_stop():
            if self.should_pause():
                continue
            ret, frame = self.camera.read()
            if not ret:
                logger.warning("Failed to read frame from camera.")
                return
            self._camera_frame_queue.put(frame)
            time.sleep(self.read_delay)

    async def up(self):
        self.start()

    async def step(self):
        if self._camera_frame_queue.empty():
            return
        frame = self._camera_frame_queue.get()
        event = CameraFrameEvent(frame=frame)
        self.bus.dispatch(event)

    async def down(self):
        await super().down()
        self.camera.release()


__all__ = ["CameraService"]
