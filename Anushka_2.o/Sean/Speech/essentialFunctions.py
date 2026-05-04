from __future__ import annotations

import datetime
from contextlib import contextmanager
import random
import sys
import time
import ctypes
import os
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import pyttsx3
from playsound import playsound

from anushka_runtime.config import CONTROL_FILES, TTS_ENGINE
from anushka_runtime.ipc import append_message
from anushka_runtime.openai_bridge import OpenAIRobotBridge
from runtime_helpers import ListCheck, retOutOf


def _suppress_alsa_warnings() -> None:
    # ALSA can emit noisy backend warnings to stderr on some Linux setups.
    # This keeps terminal logs readable while preserving runtime behavior.
    try:
        error_handler_type = ctypes.CFUNCTYPE(
            None,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
        )

        def _error_handler(_filename, _line, _function, _err, _fmt):
            return None

        global _alsa_error_handler
        _alsa_error_handler = error_handler_type(_error_handler)
        ctypes.cdll.LoadLibrary("libasound.so").snd_lib_error_set_handler(_alsa_error_handler)
    except Exception:
        pass


_suppress_alsa_warnings()

TTS_LOCK_PATH = Path(os.getenv("ANUSHKA_TTS_LOCK_PATH", str(Path(tempfile.gettempdir()) / "anushka_tts.lock")))
tts_bridge = OpenAIRobotBridge()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@contextmanager
def _speech_lock():
    TTS_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TTS_LOCK_PATH.open("a", encoding="utf-8") as lock_file:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _pick_female_voice_id(available_voices: list) -> str:
    env_voice = os.getenv("ANUSHKA_TTS_VOICE_ID", "").strip()
    if env_voice:
        # Explicit override should always win.
        return env_voice

    candidate_ids: list[str] = []

    # Espeak common female voice variants.
    candidate_ids.extend(
        [
            "english+f4",
            "english+f3",
            "en-us+f4",
            "en-us+f3",
            "english-us+f4",
            "english-us+f3",
            "en+f4",
            "en+f3",
        ]
    )

    # First try exact/contains matches from the available voice list.
    for candidate in candidate_ids:
        for voice in available_voices:
            voice_id = getattr(voice, "id", "")
            voice_name = getattr(voice, "name", "")
            if candidate.lower() in f"{voice_id} {voice_name}".lower():
                return voice_id

    # Fallback: heuristic female match by metadata.
    for voice in available_voices:
        descriptor = f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')} {getattr(voice, 'gender', '')}".lower()
        if any(token in descriptor for token in ["female", "+f3", "+f4", "+f5"]):
            return getattr(voice, "id", "")

    # Language-aware fallback keeps speech in English if possible.
    for voice in available_voices:
        descriptor = f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')}".lower()
        if "english" in descriptor or "en-us" in descriptor or descriptor.startswith("en"):
            return getattr(voice, "id", "")

    return ""

try:
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    MALE_VOICE_ID = getattr(voices[0], "id", "") if voices else ""
    FEMALE_VOICE_ID = _pick_female_voice_id(voices)
    TTS_RATE = _int_env("ANUSHKA_TTS_RATE", 145)
    TTS_VOLUME = _float_env("ANUSHKA_TTS_VOLUME", 0.95)
    if FEMALE_VOICE_ID:
        engine.setProperty("voice", FEMALE_VOICE_ID)
    engine.setProperty("rate", max(110, min(220, TTS_RATE)))
    engine.setProperty("volume", max(0.1, min(1.0, TTS_VOLUME)))
    TTS_AVAILABLE = True
except Exception:
    engine = None
    voices = []
    MALE_VOICE_ID = ""
    FEMALE_VOICE_ID = ""
    TTS_RATE = 145
    TTS_VOLUME = 0.95
    TTS_AVAILABLE = False


def writeToHaath(gesture: str) -> None:
    append_message(CONTROL_FILES["haath"], gesture)


def writeToEye(gesture: str) -> None:
    append_message(CONTROL_FILES["eye"], gesture)


def writeToJaw(gesture: str) -> None:
    append_message(CONTROL_FILES["jaw"], gesture)


def _speech_time_seconds(sentence: str) -> int:
    word_count = max(1, len(sentence.split()))
    return max(1, round(word_count / 2.4))


def _speak_with_pyttsx3(sentence: str) -> bool:
    if not (TTS_AVAILABLE and engine is not None):
        return False
    try:
        engine.stop()
    except Exception:
        pass
    try:
        if FEMALE_VOICE_ID:
            engine.setProperty("voice", FEMALE_VOICE_ID)
        engine.setProperty("rate", max(110, min(220, TTS_RATE)))
        engine.setProperty("volume", max(0.1, min(1.0, TTS_VOLUME)))
    except Exception:
        pass
    try:
        engine.say(sentence)
        engine.runAndWait()
        return True
    except Exception as exc:
        sys.stderr.write(f"[speech] pyttsx3 failed: {exc!s}\n")
        return False


def _speak_with_openai(sentence: str) -> bool:
    if not (TTS_ENGINE == "openai" and tts_bridge.available):
        return False
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
        temp_path = Path(temp_audio.name)
    try:
        tts_bridge.speech_to_file(sentence, temp_path)
        playsound(str(temp_path))
        return True
    except Exception as exc:
        sys.stderr.write(f"[speech] OpenAI TTS failed ({exc!s}); falling back.\n")
        return False
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _speak_text(sentence: str) -> None:
    if not sentence:
        return
    try:
        with _speech_lock():
            if _speak_with_openai(sentence):
                return
            if _speak_with_pyttsx3(sentence):
                return
            # Last-resort visibility: log so the operator knows speech was lost.
            sys.stderr.write(f"[speech] No working TTS backend; line lost: {sentence!r}\n")
    except Exception as exc:
        try:
            sys.stderr.write(f"[speech] _speak_text crashed: {exc!s}\n")
        except Exception:
            pass


def speak(sentence: str) -> None:
    if not sentence:
        return
    writeToJaw(str(_speech_time_seconds(sentence)))
    time.sleep(0.15)
    _speak_text(sentence)


def _apply_contextual_gesture(sentence: str, speech_time: int) -> None:
    lowered = f" {sentence.lower()} "
    if speech_time > 15:
        writeToHaath(retOutOf(["13", "29"]))

    if "give me a call" in lowered:
        writeToHaath("30")
    elif ("jai hind" in lowered) or ("jay hind" in lowered):
        writeToHaath("19")
    elif ListCheck([" i ", " me ", " myself "], lowered):
        writeToHaath("11")
    elif ListCheck(["all the best", "best of luck"], lowered):
        writeToHaath("15")
    elif (" left " in lowered) and ("left out" not in lowered) and ("left over" not in lowered):
        writeToHaath("4")
        writeToEye("1")
    elif (" right " in lowered) and ("right now" not in lowered):
        writeToHaath("5")
        writeToEye("2")
    elif " up " in lowered:
        writeToEye("4")
    elif " down " in lowered:
        writeToEye("5")
    elif "provide" in lowered:
        writeToHaath("23")
    elif ListCheck(["must", "should"], lowered):
        writeToHaath("8")
    elif ListCheck(["okay", "fine"], lowered):
        writeToHaath("16")
    elif ListCheck(["happy", "glad"], lowered):
        writeToHaath("22")
    elif ListCheck(["whole", "entire", " full ", " five ", " all "], lowered):
        writeToHaath("20")
    elif "great" in lowered:
        writeToHaath("17")
    elif ("understand" in lowered) or (" amount " in lowered):
        writeToHaath("18")
    elif " one " in lowered:
        writeToHaath("24")
    elif " two " in lowered:
        writeToHaath("25")
    elif " three " in lowered:
        writeToHaath("26")
    elif " four " in lowered:
        writeToHaath("27")
    elif ListCheck(["strength", "strong", " muscle ", "bicep"], lowered):
        writeToHaath("31")


def speakAndGest(sentence: str) -> None:
    if not sentence:
        return
    speech_time = _speech_time_seconds(sentence)
    writeToJaw(str(speech_time))
    _apply_contextual_gesture(sentence, speech_time)
    time.sleep(0.15)
    _speak_text(sentence)


def speakOutOf(options: list[str]) -> None:
    if options:
        speakAndGest(random.choice(options))


def speak_offline(sentence: str) -> None:
    """Speak ``sentence`` using ONLY the local pyttsx3 backend, never OpenAI.

    Use this for startup chatter, greetings, and any moment where network or
    OpenAI latency must not block the robot.
    """
    if not sentence:
        return
    writeToJaw(str(_speech_time_seconds(sentence)))
    time.sleep(0.15)
    try:
        with _speech_lock():
            if _speak_with_pyttsx3(sentence):
                return
            sys.stderr.write(f"[speech] Offline TTS unavailable; line lost: {sentence!r}\n")
    except Exception as exc:
        try:
            sys.stderr.write(f"[speech] speak_offline crashed: {exc!s}\n")
        except Exception:
            pass


def set2Male() -> None:
    if TTS_AVAILABLE and engine is not None and MALE_VOICE_ID:
        engine.setProperty("voice", MALE_VOICE_ID)


def set2Female() -> None:
    if TTS_AVAILABLE and engine is not None and FEMALE_VOICE_ID:
        engine.setProperty("voice", FEMALE_VOICE_ID)


def greet() -> None:
    hour = datetime.datetime.now().hour
    if 6 < hour < 12:
        speak("A very good morning")
    elif 12 <= hour < 16:
        speak("A very good afternoon")
    else:
        speak("A very good evening")


if __name__ == "__main__":
    while True:
        speak(input("Enter text: ").strip())
