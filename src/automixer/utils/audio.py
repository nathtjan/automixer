import numpy as np
from scipy.io import wavfile
import io


def numpy_to_wav_buffer(
    samplerate: int,
    audio_data: np.ndarray,
    filename: str = "audio.wav",
) -> io.BytesIO:
    wav_buffer = io.BytesIO()
    wavfile.write(wav_buffer, samplerate, audio_data)
    wav_buffer.name = filename
    return wav_buffer
