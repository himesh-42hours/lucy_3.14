# save_audio.py

import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000

print("Speak for 5 seconds...")

audio = sd.rec(
    5 * SAMPLE_RATE,
    samplerate=SAMPLE_RATE,
    channels=6,
    dtype="float32",
)

sd.wait()

sf.write("channel0.wav", audio[:, 0], SAMPLE_RATE)
sf.write("channel1.wav", audio[:, 1], SAMPLE_RATE)
sf.write("channel2.wav", audio[:, 2], SAMPLE_RATE)
sf.write("channel3.wav", audio[:, 3], SAMPLE_RATE)
sf.write("channel4.wav", audio[:, 4], SAMPLE_RATE)
sf.write("channel5.wav", audio[:, 5], SAMPLE_RATE)

print("Done.")