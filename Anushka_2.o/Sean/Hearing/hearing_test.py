from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np
import time

SAMPLE_RATE = 16000
RECORD_SECONDS = 4

print("Loading model...")

model = WhisperModel(
    "small.en",
    device="cpu",
    compute_type="int8"
)

print("Ready.")

while True:

    input("\nPress ENTER and speak...")

    print("Listening...")

    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=6,
        dtype="float32",
    )

    sd.wait()
    audio = audio[:, 0]
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.95

    audio = np.squeeze(audio)

    start = time.time()

    segments, info = model.transcribe(
        audio,
        beam_size=5,
        language="en",
        vad_filter=True,
        initial_prompt="""
        Anushka.
        Anushka Robot.
        KIET Group of Institutions.
        KIET Ghaziabad.
        Doctor Manoj Goyal.
        Sareesh Agarwal.
        Himesh Vijay.
        Humanoid Robot.
        Reception Robot.
        """
    )

    text = " ".join(
        segment.text
        for segment in segments
    ).strip()

    elapsed = time.time() - start

    print()
    print(f"Time: {elapsed:.2f}s")
    print(f"Heard: {text}")