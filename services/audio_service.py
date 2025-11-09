"""Audio service that wraps the existing Recorder and exposes a recording queue.

This service does not consume or publish audio events itself; instead it
provides the recording queue that transcription services can consume. This
keeps a single source-of-truth queue and avoids duplicating the audio stream.
"""
import queue
from recorder import Recorder


class AudioService:
    def __init__(self, device_index: int, block_duration: int = 10):
        # internal queue that Recorder will put mono chunks into
        self.recording_queue = queue.Queue()
        self.recorder = Recorder(device_index, self.recording_queue, block_duration=block_duration)

    def start(self):
        self.recorder.start()

    def stop(self):
        self.recorder.stop()

    def get_recording_queue(self):
        return self.recording_queue
