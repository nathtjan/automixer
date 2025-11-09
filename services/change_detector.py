"""Port of the change-detection logic from the original main loop.

Subscribes to CameraFrameEvent and publishes ChangeDetectedEvent when a
significant visual change is detected (using sobel edges + frame diff).
"""
import time
import numpy as np
import cv2
from core.events import CameraFrameEvent, ChangeDetectedEvent
from sobel import sobel_edge
import logging
from typing import Optional


class ChangeDetector:
    def __init__(
        self,
        event_bus,
        edge_threshold: int = 20,
        diff_threshold: float = 5.0,
        full_black_threshold_mean: float = 36.0,
        full_black_threshold_std: float = 5.0,
        obs_vcam_default_path: Optional[str] = None,
        cooldown: float = 2.0,
    ):
        self.logger = logging.getLogger("services.change_detector")
        self.bus = event_bus
        self.edge_threshold = edge_threshold
        self.diff_threshold = diff_threshold
        self.full_black_threshold_mean = full_black_threshold_mean
        self.full_black_threshold_std = full_black_threshold_std
        self.obs_vcam_default = None
        if obs_vcam_default_path:
            try:
                self.obs_vcam_default = cv2.imread(obs_vcam_default_path)
            except Exception:
                self.obs_vcam_default = None

        self.img_before = None
        self._last_event_ts = 0.0
        self.cooldown = float(cooldown)
        self.bus.subscribe(CameraFrameEvent, self.on_frame)

    def is_full_black(self, img: np.ndarray) -> bool:
        mean = float(np.mean(img))
        std = float(np.std(img))
        return (mean < self.full_black_threshold_mean and std < self.full_black_threshold_std)

    def is_obs_vcam_default(self, img: np.ndarray) -> bool:
        if self.obs_vcam_default is None:
            return False
        try:
            diff = img.astype(np.int16) - self.obs_vcam_default.astype(np.int16)
            return (diff.mean() <= 1.0 and diff.std() <= 0.5)
        except Exception:
            return False

    def on_frame(self, event: CameraFrameEvent):
        img = event.frame
        if img is None:
            return

        try:
            if (
                self.img_before is not None
                and not self.is_full_black(self.img_before)
                and not self.is_full_black(img)
                and not self.is_obs_vcam_default(self.img_before)
                and not self.is_obs_vcam_default(img)
            ):
                img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                edge_gray = sobel_edge(img_gray)
                # convert edge to 3-channel so shapes match
                edge = cv2.cvtColor(edge_gray, cv2.COLOR_GRAY2BGR)

                diff = np.abs(img.astype(np.int16) - self.img_before.astype(np.int16)).astype(np.uint8)
                # mask using edge threshold
                mask = edge < self.edge_threshold
                diff = diff * mask
                mean_diff = float(np.mean(diff))
                if mean_diff > self.diff_threshold:
                    now = time.time()
                    if now - self._last_event_ts >= self.cooldown:
                        self.logger.info(f"ChangeDetector: change detected (mean_diff={mean_diff:.2f})")
                        evt = ChangeDetectedEvent(timestamp=now)
                        self.bus.publish(evt)
                        self._last_event_ts = now
                    else:
                        self.logger.debug("ChangeDetector: change ignored due to cooldown")
        except Exception:
            # keep detector resilient
            self.logger.exception("Error while processing frame in ChangeDetector")
        finally:
            self.img_before = img
