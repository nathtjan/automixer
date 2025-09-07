import numpy as np
import logging
import queue
import whisper
import threading
import time
import torch


class Transcriber:
    def __init__(self, recording_queue, transcription_queue, model=None):
        self.recording_queue = recording_queue
        self.transcription_queue = transcription_queue
        if not model:
            use_cuda = torch.cuda.is_available()
            device = "cuda" if use_cuda else "cpu"
            logging.info(f"Using device: {device}")
            model = whisper.load_model("small", device=device)
        self.model = model
        self._should_stop = False
        self._thread = None

    def run(self):
        while True:
            if self._should_stop:
                break
            audio_chunk = []
            # Collect enough audio for one transcription
            for _ in range(200):
                if self.recording_queue.empty():
                    break
                chunk = self.recording_queue.get()
                chunk_np = np.array(chunk).astype(np.float32)
                abs_mean_chunk = np.abs(chunk_np).mean()
                if abs_mean_chunk <  1e-3:
                    logging.debug("Empty chunk skipped")
                    continue
                audio_chunk.extend(chunk)

            # Skip if no audio
            if not audio_chunk:
                logging.debug("No audio in queue, transcription skipped")
                continue

            audio_np = np.array(audio_chunk).astype(np.float32)

            # Skip empty audio
            abs_mean_audio = np.abs(audio_np).mean()
            logging.debug(f"abs_mean_audio: {abs_mean_audio}")
            if abs_mean_audio <  1e-3:
                logging.debug("Empty audio skipped")
                continue

            # Clean audio (replace NaN with 0)
            audio_np[audio_np!=audio_np] = 0

            # Run Whisper transcription
            logging.debug("Transcribing...")
            result = self.model.transcribe(audio_np, language="id", fp16=False)
            result = result['text'].strip()
            self.transcription_queue.put(result)
            

    def is_alive(self):
        return (self._thread is not None) and self._thread.is_alive()

    def start(self):
        if self.is_alive():
            return
        self._should_stop = False
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        logging.info("Transcriber started")

    def stop(self):
        if not self.is_alive():
            return
        self._should_stop = True
        self._thread.join()
        self._thread = None
        logging.info("Transcriber stopped")
