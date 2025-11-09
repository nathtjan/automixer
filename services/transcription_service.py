"""Transcription service that wraps either OpenAITranscriber or LocalTranscriber
and publishes TranscriptionEvent to the event bus when new transcripts arrive.
"""
import threading
import queue
import time
import logging
from core.events import TranscriptionEvent

try:
    from transcriber import OpenAITranscriber, LocalTranscriber
except Exception:
    OpenAITranscriber = None
    LocalTranscriber = None


class TranscriptionService:
    def __init__(self, event_bus, recording_queue: queue.Queue, use_local: bool = False):
        self.event_bus = event_bus
        self.recording_queue = recording_queue
        self.transcription_queue = queue.Queue()
        self.use_local = use_local
        self._thread = None
        self._stop = threading.Event()

        # choose transcriber implementation
        self.transcriber = None
        try:
            if use_local:
                if LocalTranscriber is None:
                    raise RuntimeError("LocalTranscriber not available")
                self.transcriber = LocalTranscriber(self.recording_queue, self.transcription_queue)
            else:
                # try OpenAI first, but fall back to LocalTranscriber if OpenAI fails
                try:
                    if OpenAITranscriber is None:
                        raise RuntimeError("OpenAITranscriber not available")
                    self.transcriber = OpenAITranscriber(self.recording_queue, self.transcription_queue)
                except Exception as e:
                    logging.warning(f"OpenAITranscriber failed to initialize: {e}")
                    if LocalTranscriber is not None:
                        logging.info("Falling back to LocalTranscriber")
                        self.transcriber = LocalTranscriber(self.recording_queue, self.transcription_queue)
                    else:
                        logging.error("No transcriber available (OpenAI/Local) — transcription disabled")
                        self.transcriber = None
        except Exception as e:
            logging.exception("Failed to initialize transcriber")
            self.transcriber = None

    def start(self):
        # start the underlying transcriber (if available)
        if self.transcriber is None:
            logging.warning("TranscriptionService.start() called but no transcriber is configured")
            return
        try:
            self.transcriber.start()
        except Exception:
            logging.exception("Failed to start transcriber")
            return
        # start thread that forwards transcription_queue items into events
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        try:
            self.transcriber.stop()
        except Exception:
            pass
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run(self):
        while not self._stop.is_set():
            try:
                text = self.transcription_queue.get(timeout=0.5)
                if not text:
                    continue
                evt = TranscriptionEvent(text=text, timestamp=time.time())
                self.event_bus.publish(evt)
            except queue.Empty:
                continue
            except Exception:
                continue
