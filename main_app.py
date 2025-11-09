"""Bootstrapper for the event-driven automixer.

This file wires the EventBus, services and a Mixer client together and
demonstrates a minimal runtime loop. It's intended as a scaffold to iterate on.
"""
import time
import logging
from core.event_bus import EventBus
from core.events import RougeScoreEvent, SceneChangeRequest, TranscriptionEvent, ChangeDetectedEvent
from clients.obs_adapter import OBSAdapter
from services.camera_service import CameraService
from services.vision_service import VisionService
from services.rouge_service import RougeService
from services.audio_service import AudioService
from services.transcription_service import TranscriptionService


def setup_logger():
    logger = logging.getLogger("automixer")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def main():
    logger = setup_logger()
    bus = EventBus()

    # Mixer adapter (OBS)
    mixer = OBSAdapter()  # optionally pass existing ws client
    try:
        mixer.connect()
    except Exception:
        logger.warning("Failed to connect to OBS automatically; continue in offline mode")

    # Services
    cam = CameraService(bus, device_index=0, fps=6)
    vision = VisionService(bus, langs=("id", "en"))
    rouge = RougeService(bus)
    change_detector = None
    try:
        from services.change_detector import ChangeDetector
        change_detector = ChangeDetector(bus, obs_vcam_default_path="obs_vcam_default.png")
    except Exception:
        logger.warning("ChangeDetector failed to initialize; change detection disabled")

    # Audio + Transcription
    audio = AudioService(device_index=23)
    transcription = TranscriptionService(bus, audio.get_recording_queue(), use_local=False)

    # Scene manager: centralizes switching logic and controls recorder/transcriber
    try:
        from services.scene_manager import SceneManager
        scene_manager = SceneManager(
            bus,
            mixer,
            audio_service=audio,
            transcription_service=transcription,
            ppt_scenes=("FULL PPT", "KHOTBAH MODE 1", "KHOTBAH MODE 2"),
            cam_scene="UTAMA DECKLINK",
            onchange_delay=2.0,
            transition_back_delay=1.0,
            rouge_threshold=0.8,
        )
    except Exception:
        logger.warning("SceneManager failed to initialize; scene automation disabled")

    # Example reaction: when RougeScoreEvent crosses threshold request scene change
    def on_rouge(event: RougeScoreEvent):
        logger.debug(f"Rouge score computed: {event.score:.3f} details={event.details}")
        if event.score >= rouge.rouge_threshold:
            logger.info("Rouge threshold crossed; requesting scene change to camera")
            try:
                mixer.set_program_scene("UTAMA DECKLINK")
            except Exception as e:
                logger.exception("Failed to set scene on mixer")

    bus.subscribe(RougeScoreEvent, on_rouge)

    # Reaction to visual change: switch to PPT
    PPT_SCENENAMES = ["FULL PPT", "KHOTBAH MODE 1", "KHOTBAH MODE 2"]
    DEFAULT_PPT = PPT_SCENENAMES[0]

    def on_change(evt: ChangeDetectedEvent):
        logger.info("Change detected event received; switching to PPT scene")
        try:
            curr = None
            try:
                curr = mixer.get_current_program_scene()
            except Exception:
                curr = None
            if curr in PPT_SCENENAMES:
                logger.info(f"Program scene unchanged since current is {curr}")
                return
            mixer.set_program_scene(DEFAULT_PPT)
        except Exception:
            logger.exception("Failed to switch to PPT on change event")

    bus.subscribe(ChangeDetectedEvent, on_change)

    # subscribe to transcription events (for debugging/logging)
    def on_transcription(evt: TranscriptionEvent):
        logger.info(f"Transcription event: {evt.text}")

    bus.subscribe(TranscriptionEvent, on_transcription)

    # Start capture (audio/transcription are managed by SceneManager based on scenes)
    cam.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        cam.stop()
        try:
            mixer.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
