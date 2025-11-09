import threading
import time
import cv2
from core.events import CameraFrameEvent


class CameraService:
    """Captures frames from a camera device and publishes CameraFrameEvent."""

    def __init__(self, event_bus, device_index=0, fps=10):
        self.event_bus = event_bus
        self.device_index = device_index
        self.fps = fps
        self._thread = None
        self._stop = threading.Event()
        self._cap = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._cap:
            self._cap.release()

    def _run(self):
        self._cap = cv2.VideoCapture(self.device_index)
        interval = 1.0 / max(1, self.fps)
        while not self._stop.is_set():
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            evt = CameraFrameEvent(frame=frame, timestamp=time.time())
            self.event_bus.publish(evt)
            time.sleep(interval)
