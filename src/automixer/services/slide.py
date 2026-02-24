import asyncio
from logging import getLogger
import importlib.resources
import numpy as np
import cv2
from automixer.core.events import (
    SlideChangeEvent, CameraFrameEvent, ProgramChangeEvent
)
from automixer.services.base import BaseService, autoregister
from automixer.utils.vision import sobel_edge


logger = getLogger(__name__)


class SlideService(BaseService):
    def __init__(
        self,
        bus,
        diff_threshold=5,
        edge_threshold=20,
        full_black_threshold_mean=36,
        full_black_threshold_std=5,
        cam_frame_timeout=5.0
    ):
        super().__init__(bus)
        self.prev_frame = None
        self.diff_threshold = diff_threshold
        self.edge_threshold = edge_threshold
        self.full_black_threshold_mean = full_black_threshold_mean
        self.full_black_threshold_std = full_black_threshold_std
        self.cam_frame_timeout = cam_frame_timeout
        self.obs_vcam_default_template = cv2.imread(str(
            importlib.resources.files("automixer.resources").joinpath("obs_vcam_default.png")
        ))
        if self.obs_vcam_default_template is None:
            logger.warning("Failed to load OBS VCam default template image.")

    def is_obs_vcam_default(self, frame):
        if self.obs_vcam_default_template is None:
            return False
        # Simple template matching approach
        result = cv2.matchTemplate(frame, self.obs_vcam_default_template, cv2.TM_CCOEFF_NORMED)
        return np.max(result) > 0.9  # Threshold for match confidence

    def is_full_black(self, frame):
        mean = np.mean(frame)
        std = np.std(frame)
        return (mean < self.full_black_threshold_mean
                and std < self.full_black_threshold_std)

    def frame_is_valid(self, frame):
        return (
            frame is not None
            and not self.is_full_black(frame)
            and not self.is_obs_vcam_default(frame)
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
    async def on_camera_frame(self, event: CameraFrameEvent):
        frame = event.frame

        if not self.frame_is_valid(frame):
            return

        if self.prev_frame is None:
            self.prev_frame = frame
            return

        if self.frames_are_different(frame, self.prev_frame):
            new_event = SlideChangeEvent(
                slide=frame,
                previous_slide=self.prev_frame
            )
            self.bus.dispatch(new_event)

        self.prev_frame = frame

    @autoregister
    async def on_program_change(self, event: ProgramChangeEvent):
        """Assumes slide change"""

        try:
            cam_frame_event = await self.bus.expect(
                CameraFrameEvent,
                include=lambda e: self.frame_is_valid(e.frame),
                timeout=self.cam_frame_timeout
            )
            frame = cam_frame_event.frame
        except asyncio.TimeoutError:
            logger.warning("Failed to get a valid camera frame after program change.")
            return

        new_event = SlideChangeEvent(
            slide=frame,
            previous_slide=self.prev_frame
        )
        self.bus.dispatch(new_event)
        self.prev_frame = frame


__all__ = ["SlideService"]
