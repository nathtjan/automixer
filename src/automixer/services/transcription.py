from logging import getLogger
from queue import Queue
import time
import numpy as np
from automixer.core.events import (
    AudioSegmentEvent,
    ProgramChangeEvent,
    SceneType,
    TranscriptionEvent,
)
from automixer.services.base import ThreadService, autoregister
from automixer.utils.audio import numpy_to_wav_buffer


logger = getLogger(__name__)


class TranscriptionService(ThreadService):
    SERVICE_NAME = "transcription"

    def __init__(self, bus, transcriber, run_delay: float = 0.1):
        super().__init__(bus)
        self.transcriber = transcriber
        self._audio_queue = Queue()
        self._transcription_queue = Queue()
        self._run_delay = run_delay

    @autoregister
    def on_audio_segment(self, event: AudioSegmentEvent):
        self._audio_queue.put(event)

    @autoregister
    def on_program_change(self, event: ProgramChangeEvent):
        if event.scene_type is SceneType.CAMERA:
            self.stop()
            self.empty_queue()
        elif event.scene_type is SceneType.SLIDE:
            self.start()

    def empty_queue(self):
        while not self._audio_queue.empty():
            self._audio_queue.get()
        while not self._transcription_queue.empty():
            self._transcription_queue.get()

    def step(self):
        while not self._transcription_queue.empty():
            self.bus.dispatch(self._transcription_queue.get())

    def run(self):
        while not self.should_stop():
            if not self._audio_queue.empty():
                event = self.process_audio_event(self._audio_queue.get())
                if event:
                    self._transcription_queue.put(event)
            time.sleep(self._run_delay)

    def process_audio_event(self, event: AudioSegmentEvent):
        segment = event.segment
        samplerate = event.samplerate
        duration = len(segment) / samplerate

        # Skip if no audio
        if not segment:
            logger.debug("Audio segment empty, transcription skipped")
            return

        audio_np = np.array(segment).astype(np.float32)
        # Convert to mono if multi-channel
        if audio_np.ndim > 1:
            audio_np = np.mean(audio_np, axis=1)

        # Clean audio (replace NaN with 0)
        audio_np[audio_np != audio_np] = 0

        logger.debug(f"Transcribing segment of length {duration:.2f} seconds")
        try:
            wav_buffer = numpy_to_wav_buffer(samplerate, audio_np)
            response = self.transcriber(wav_buffer)
            result = response.text.strip()
            return TranscriptionEvent(text=result)
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")


# Helper class for OpenAI transcription
class OpenAITranscriber:
    def __init__(self, client, model: str, **params):
        self.client = client
        self.params = params
        self.params["model"] = model

    def __call__(self, wav_buffer):
        self.params["file"] = wav_buffer
        response = self.client.audio.transcriptions.create(**self.params)

        # Buffer is potentially large, remove after use
        self.params.pop("file", None)

        return response


__all__ = [
    "TranscriptionService",
    "OpenAITranscriber"
]
