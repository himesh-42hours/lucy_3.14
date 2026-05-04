from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import speech_recognition as sr

from anushka_runtime.device_discovery import microphone_selection
from anushka_runtime.openai_bridge import OpenAIRobotBridge


bridge = OpenAIRobotBridge()


def s2t() -> str:
    """One-shot speech-to-text. Returns "" on any failure."""
    selection = microphone_selection()
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone(device_index=selection.index) as source:
            recognizer.dynamic_energy_threshold = True
            recognizer.pause_threshold = 0.5
            recognizer.non_speaking_duration = 0.3
            recognizer.adjust_for_ambient_noise(source, duration=0.6)
            audio = recognizer.listen(source, timeout=6, phrase_time_limit=15)
    except sr.WaitTimeoutError:
        return ""
    except Exception:
        return ""

    if bridge.available:
        try:
            return bridge.transcribe_wav(audio.get_wav_data())
        except Exception:
            pass
    try:
        return recognizer.recognize_google(audio)
    except Exception:
        return ""


def hinToEng(text: str) -> str:
    if not text:
        return ""
    if bridge.available:
        try:
            return bridge.normalize_to_english(text)
        except Exception:
            return text
    return text
