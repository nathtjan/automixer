"""Central scene manager that reacts to ChangeDetectedEvent and RougeScoreEvent.

It controls the mixer (OBS/vMix via MixerClient) and manages audio/transcription
services lifecycle to mirror the behavior in the original `main.py`.
"""
import time
import logging
from core.events import ChangeDetectedEvent, RougeScoreEvent
from typing import Sequence


class SceneManager:
    def __init__(
        self,
        event_bus,
        mixer,
        audio_service=None,
        transcription_service=None,
        ppt_scenes: Sequence[str] = ("FULL PPT", "KHOTBAH MODE 1", "KHOTBAH MODE 2"),
        cam_scene: str = "UTAMA DECKLINK",
        onchange_delay: float = 2.0,
        transition_back_delay: float = 1.0,
        rouge_threshold: float = 0.8,
    ):
        self.logger = logging.getLogger("services.scene_manager")
        self.bus = event_bus
        self.mixer = mixer
        self.audio = audio_service
        self.transcription = transcription_service
        self.ppt_scenes = list(ppt_scenes)
        self.cam_scene = cam_scene
        self.onchange_delay = float(onchange_delay)
        self.transition_back_delay = float(transition_back_delay)
        self.rouge_threshold = float(rouge_threshold)

        self.rouge_threshold_crossed_timestamp = None

        self.bus.subscribe(ChangeDetectedEvent, self.on_change)
        self.bus.subscribe(RougeScoreEvent, self.on_rouge)

    def _start_recording(self):
        try:
            if self.audio:
                self.audio.start()
            if self.transcription:
                self.transcription.start()
        except Exception:
            self.logger.exception("Failed to start audio/transcription")

    def _stop_recording(self):
        try:
            if self.audio:
                self.audio.stop()
            if self.transcription:
                self.transcription.stop()
        except Exception:
            self.logger.exception("Failed to stop audio/transcription")

    def on_change(self, event: ChangeDetectedEvent):
        self.logger.info("SceneManager: change detected -> switch to PPT")
        try:
            # if currently already on ppt, do nothing
            try:
                curr = self.mixer.get_current_program_scene()
            except Exception:
                curr = None

            if curr in self.ppt_scenes:
                self.logger.info(f"Program scene unchanged since current is {curr}")
                return

            # switch to PPT and start recording/transcription
            self.mixer.set_program_scene(self.ppt_scenes[0])
            self.rouge_threshold_crossed_timestamp = None
            # start recorder/transcriber
            self._start_recording()
            # small delay to allow transitions to settle
            time.sleep(self.onchange_delay)
        except Exception:
            self.logger.exception("Failed to handle change detected event")

    def on_rouge(self, event: RougeScoreEvent):
        score = event.score
        self.logger.debug(f"SceneManager: rouge score {score:.3f}")
        try:
            # Only consider switch-back when score crosses threshold
            if score >= self.rouge_threshold:
                if self.rouge_threshold_crossed_timestamp is None:
                    self.logger.info("Rouge score crosses threshold; starting timer")
                    self.rouge_threshold_crossed_timestamp = time.time()
                else:
                    elapsed = time.time() - self.rouge_threshold_crossed_timestamp
                    if elapsed >= self.transition_back_delay:
                        # perform switch to camera
                        try:
                            curr = self.mixer.get_current_program_scene()
                        except Exception:
                            curr = None
                        if curr != self.cam_scene:
                            self.logger.info("SceneManager: switching to camera scene")
                            self.mixer.set_program_scene(self.cam_scene)
                        # stop recording/transcription since we're back on camera
                        self._stop_recording()
                        # reset timer
                        self.rouge_threshold_crossed_timestamp = None
            else:
                # reset if score drops
                self.rouge_threshold_crossed_timestamp = None
        except Exception:
            self.logger.exception("Failed to handle rouge event")
