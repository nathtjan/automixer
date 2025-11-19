from logging import getLogger
from automixer.core.events import CameraFrameEvent
from automixer.services.base import BaseService
import cv2


logger = getLogger(__name__)


class CameraService(BaseService):
    def __init__(
        self,
        bus,
        camera: cv2.VideoCapture,
    ):
        super().__init__(bus)
        self.camera = camera

    def step(self):
        ret, frame = self.camera.read()
        if not ret:
            logger.warning("Failed to read frame from camera.")
            return
        event = CameraFrameEvent(frame=frame)
        self.bus.dispatch(event)


__all__ = ["CameraService"]
