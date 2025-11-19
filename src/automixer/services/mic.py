from logging import getLogger
from queue import Queue
from automixer.core.events import AudioSegmentEvent, ProgramChangeEvent, SceneType
from automixer.services.base import ThreadService, autoregister
import sounddevice as sd


logger = getLogger(__name__)


class MicService(ThreadService):
    SERVICE_NAME = "mic"

    def __init__(
        self,
        bus,
        input_stream: sd.InputStream,
        read_frames: int,
    ):
        super().__init__(bus)
        self.input_stream = input_stream
        self.read_frames = read_frames
        self._audio_queue = Queue()

    def run(self):
        while not self.should_stop():
            segment, _ = self.input_stream.read(self.read_frames)
            self._audio_queue.put(segment.copy())

    def step(self):
        while not self._audio_queue.empty():
            event = AudioSegmentEvent(
                segment=self._audio_queue.get(),
                samplerate=self.samplerate
            )
            self.bus.dispatch(event)

    def empty_queue(self):
        while not self._audio_queue.empty():
            self._audio_queue.get()

    @autoregister
    def on_program_change(self, event: ProgramChangeEvent):
        if event.scene_type is SceneType.CAMERA:
            self.stop()
            self.empty_queue()
        elif event.scene_type is SceneType.SLIDE:
            self.start()


__all__ = ["MicService"]
