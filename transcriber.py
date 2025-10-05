import numpy as np
import logging
import queue
import whisper
import threading
import time
import torch
from openai import OpenAI
from utils import numpy_to_wav_buffer


class LocalTranscriber:
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


class OpenAITranscriber:
    def __init__(
        self,
        recording_queue,
        transcription_queue,
        model="gpt-4o-transcribe",
        max_retry_pop=10,
        retry_pop_delay=0.01
    ):
        self.recording_queue = recording_queue
        self.transcription_queue = transcription_queue
        self.model = model
        self.client = OpenAI()
        self.max_retry_pop = max_retry_pop
        self.retry_pop_delay = retry_pop_delay
        self._should_stop = False
        self._thread = None

    def run(self):
        while True:
            if self._should_stop:
                break
            audio_chunk = []
            # Collect enough audio for one transcription
            for _ in range(100):
                for _ in range(1 + self.max_retry_pop):  # first attempt + retries
                    if not self.recording_queue.empty():
                        break
                    time.sleep(self.retry_pop_delay)
                else:
                    break
                chunk = self.recording_queue.get()
                audio_chunk.extend(chunk)

            # Skip if no audio
            if not audio_chunk:
                logging.debug("No audio in queue, transcription skipped")
                continue

            audio_np = np.array(audio_chunk).astype(np.float32)

            # Clean audio (replace NaN with 0)
            audio_np[audio_np!=audio_np] = 0

            # Run Whisper transcription
            logging.debug("Transcribing...")
            
            try:
                wav_buffer = numpy_to_wav_buffer(16000, audio_np)
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=wav_buffer,
                    language="id"
                )
                result = response.text.strip()
                self.transcription_queue.put(result)
            except Exception as e:
                logging.error(f"Error during transcription: {str(e)}")
                continue
            

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
