import sounddevice as sd
import numpy as np
import logging
import queue
import threading
import time


class Recorder:
    def __init__(self, device, output_queue, block_duration=10):
        self.device = device
        self.output_queue = output_queue
        self.block_duration = block_duration
        self._should_stop = False
        self._thread = None

    def callback(self, indata, frames, time_info, status):
        if status:
            logging.error(f"Recording error: {status}")
        # Convert to mono and add to queue
        mono_audio = indata.mean(axis=1)
        self.output_queue.put(mono_audio.copy())

    def run(self):
        sd.default.device = self.device
        with sd.InputStream(samplerate=16000, channels=1, callback=self.callback):
            logging.info("Recording... Press Ctrl+C to stop.")
            while True:
                if self._should_stop:
                    break
                time.sleep(0.1)  # Keep main thread alive

    def is_alive(self):
        return (self._thread is not None) and self._thread.is_alive()

    def start(self):
        if self.is_alive():
            return
        self._should_stop = False
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        logging.info("Recorder started")

    def stop(self):
        if not self.is_alive():
            return
        self._should_stop = True
        self._thread.join()
        self._thread = None
        logging.info("Recorder stopped")
