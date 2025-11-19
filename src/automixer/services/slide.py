from logging import getLogger
import numpy as np
import cv2
from automixer.core.events import (
    SlideChangeEvent, CameraFrameEvent
)
from automixer.services.base import BaseService, autoregister
from src.automixer.utils.vision import sobel_edge


logger = getLogger(__name__)


class SlideService(BaseService):
    def __init__(
        self,
        bus,
        diff_threshold=5,
        edge_threshold=20,
        full_black_threshold_mean=36,
        full_black_threshold_std=5,
    ):
        super().__init__(bus)
        self.prev_frame = None
        self.diff_threshold = diff_threshold
        self.edge_threshold = edge_threshold
        self.full_black_threshold_mean = full_black_threshold_mean
        self.full_black_threshold_std = full_black_threshold_std

    def is_obs_vcam_default(self, frame):
        ...

    def is_full_black(self, frame):
        mean = np.mean(frame)
        std = np.std(frame)
        return (mean < self.full_black_threshold_mean
                and std < self.full_black_threshold_std)

    def frame_is_valid(self, frame):
        return (
            frame is not None
            and not self.is_full_black(frame)
            # and not self.is_obs_vcam_default(frame)
        )

    def calculate_edge(self, frame):
        # Edge detection using grayscale conversion and Sobel operator
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edge_gray = sobel_edge(frame_gray)
        edge = cv2.cvtColor(edge_gray, cv2.COLOR_GRAY2BGR)
        return edge

    def calculate_abs_diff(self, frame1, frame2):
        return np.abs(
            frame1.astype(np.int16)
            - frame2.astype(np.int16)
        ).astype(np.uint8)

    def frames_are_different(self, frame1, frame2):
        # Calculate average of absolute difference
        # considering only non-edge areas
        edge = self.calculate_edge(frame1)
        diff = self.calculate_abs_diff(frame1, frame2)
        diff *= edge < self.edge_threshold  # Ignore noises in edges
        mean_diff = np.mean(diff)
        # Threshold check
        return mean_diff > self.diff_threshold

    @autoregister
    def on_camera_frame(self, event: CameraFrameEvent):
        frame = event.frame

        if not self.frame_is_valid(frame):
            return

        if self.prev_frame is None:
            self.prev_frame = frame
            return

        if self.frames_are_different(frame, self.prev_frame):
            event = SlideChangeEvent(
                slide=frame,
                prev_slide=self.prev_frame
            )
            self.bus.dispatch(event)

        self.prev_frame = frame


__all__ = ["SlideService"]
