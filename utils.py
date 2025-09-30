import numpy as np
from scipy.io import wavfile
import io


def numpy_to_wav_buffer(samplerate, audio_data):
    wav_buffer = io.BytesIO()
    wavfile.write(wav_buffer, samplerate, audio_data)
    wav_buffer.name = "audio.wav"
    return wav_buffer
