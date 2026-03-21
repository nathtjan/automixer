from logging import getLogger
import math
from queue import Queue
from collections import deque
from threading import Lock
from automixer.core.events import AudioSegmentEvent, ProgramChangeEvent, SceneType
from automixer.services.base import ThreadService, autoregister
import sounddevice as sd


logger = getLogger(__name__)


class MicService(ThreadService):
    def __init__(
        self,
        bus,
        input_stream: sd.InputStream,
        read_frames: int,
        preroll_seconds: float = 0.0,
    ):
        super().__init__(bus)
        self.input_stream = input_stream
        self.read_frames = read_frames
        self.preroll_seconds = max(0.0, preroll_seconds)
        self._audio_queue = Queue()
        self._preroll_buffer = deque()
        self._preroll_lock = Lock()
        self._emit_audio = False

        samplerate = float(self.input_stream.samplerate)
        self._preroll_max_frames = int(math.ceil(self.preroll_seconds * samplerate))
        self._preroll_total_frames = 0

    async def up(self):
        self.start()
    
    async def down(self):
        await super().down()
        self.input_stream.close()

    def run(self):
        self.input_stream.start()
        while not self.should_stop():
            if self.should_pause():
                continue
            segment, overflowed = self.input_stream.read(self.read_frames)
            if overflowed:
                raise RuntimeError("Audio input overflowed")
            segment = segment.copy()
            self._append_preroll(segment)
            if self._emit_audio:
                self._audio_queue.put(segment)
        self.input_stream.stop()

    def _append_preroll(self, segment):
        if self._preroll_max_frames <= 0:
            return
        segment_frames = len(segment)
        with self._preroll_lock:
            self._preroll_buffer.append(segment)
            self._preroll_total_frames += segment_frames
            while self._preroll_total_frames > self._preroll_max_frames and self._preroll_buffer:
                dropped = self._preroll_buffer.popleft()
                self._preroll_total_frames -= len(dropped)

    def _enqueue_preroll(self):
        if self._preroll_max_frames <= 0:
            return
        with self._preroll_lock:
            snapshot = list(self._preroll_buffer)
        for segment in snapshot:
            self._audio_queue.put(segment)

    async def step(self):
        while not self._audio_queue.empty():
            event = AudioSegmentEvent(
                segment=self._audio_queue.get(),
                samplerate=self.input_stream.samplerate
            )
            self.bus.dispatch(event)

    def empty_queue(self):
        while not self._audio_queue.empty():
            self._audio_queue.get()

    @autoregister
    def on_program_change(self, event: ProgramChangeEvent):
        if event.scene_type is SceneType.CAMERA:
            self._emit_audio = False
            self.empty_queue()
        elif event.scene_type is SceneType.SLIDE:
            if not self._emit_audio:
                self._enqueue_preroll()
            self._emit_audio = True


__all__ = ["MicService"]
