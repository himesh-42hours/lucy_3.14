from __future__ import annotations

import datetime
import audioop
import os
import re
import signal
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import requests
import speech_recognition as sr
from playsound import playsound

from anushka_runtime.config import (
    CONTROL_FILES,
    DEBUG_HEARING,
    ENABLE_LANGUAGE_MIRROR,
    GOOGLE_STT_LANGUAGE,
    LOG_FILES,
    OPENWEATHER_API_KEY,
    OPENWEATHER_DEFAULT_CITY,
    REPLY_LANGUAGE,
    RESOURCES_DIR,
    STATUS_FILES,
)
from anushka_runtime.device_discovery import microphone_selection
from anushka_runtime.ipc import append_message, open_reader, read_available
from anushka_runtime.openai_bridge import OpenAIRobotBridge, OpenAIUnavailableError
from runtime_helpers import ListCheck, writeToEye, writeToHaath, writeToRolls
from OfflineChatbot import OfflineChatbot
import offline_qa
from Speech.essentialFunctions import speak, speakAndGest


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


HEARING_STARTUP_SPEAK = _bool_env("ANUSHKA_HEARING_STARTUP_SPEAK", False)


def _int_env(name: str, default: int | None) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


LISTEN_TIMEOUT_SECONDS = _float_env("ANUSHKA_LISTEN_TIMEOUT", 12.0)
PHRASE_TIME_LIMIT_SECONDS = _float_env("ANUSHKA_PHRASE_TIME_LIMIT", 15.0)
AMBIENT_CALIBRATION_SECONDS = _float_env("ANUSHKA_AMBIENT_CALIBRATION_SECONDS", 0.4)
USE_DYNAMIC_ENERGY_THRESHOLD = _bool_env("ANUSHKA_DYNAMIC_ENERGY_THRESHOLD", True)
ENERGY_THRESHOLD = _int_env("ANUSHKA_ENERGY_THRESHOLD", None)


bridge = OpenAIRobotBridge()
conversation_history: list[str] = []

# Load knowledge once at module startup — never re-read per turn.
def _load_knowledge_once() -> str:
    return "\n\n".join(
        part
        for part in [
            read_text(LOG_FILES["knowledge"]),
            read_text(LOG_FILES["persona"]),
        ]
        if part
    )

_KNOWLEDGE: str = ""  # populated in main() after confirming files are readable

_shutdown_requested = False


def _raise_shutdown(signum, frame) -> None:
    global _shutdown_requested
    _shutdown_requested = True


def _diag(message: str) -> None:
    """Surface a human-readable diagnostic to the hearing status file and stderr."""
    append_message(STATUS_FILES["hear"], message)
    try:
        sys.stderr.write(f"[hearing] {message}\n")
        sys.stderr.flush()
    except Exception:
        pass


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return default


def log_query(query: str) -> None:
    append_message(LOG_FILES["conversation"], f"Query: {query}")


def log_reply(reply: str) -> None:
    append_message(LOG_FILES["conversation"], f"Anooshka: {reply}")


def add_history(query: str, reply: str) -> None:
    conversation_history.append(f"User: {query}")
    conversation_history.append(f"Anooshka: {reply}")
    if len(conversation_history) > 10:
        del conversation_history[: len(conversation_history) - 10]


def localized_reply(user_query: str, english_reply: str) -> str:
    if not bridge.available:
        return english_reply
    if REPLY_LANGUAGE != "auto" or not ENABLE_LANGUAGE_MIRROR:
        return english_reply
    try:
        return bridge.mirror_language(user_query, english_reply)
    except Exception:
        return english_reply


def play_resource(relative_path: str) -> bool:
    path = RESOURCES_DIR / relative_path
    if not path.exists():
        return False
    try:
        playsound(str(path))
        return True
    except Exception:
        return False


def _build_recognizer() -> sr.Recognizer:
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = USE_DYNAMIC_ENERGY_THRESHOLD
    if ENERGY_THRESHOLD is not None:
        recognizer.energy_threshold = max(50, ENERGY_THRESHOLD)
    recognizer.pause_threshold = 0.5
    recognizer.non_speaking_duration = 0.3
    return recognizer


def _calibrate(recognizer: sr.Recognizer, mic: sr.Microphone) -> None:
    try:
        if ENERGY_THRESHOLD is not None and not USE_DYNAMIC_ENERGY_THRESHOLD:
            if DEBUG_HEARING:
                _diag(
                    "Skipping ambient calibration: using fixed energy threshold "
                    f"(energy_threshold={int(getattr(recognizer, 'energy_threshold', 0))})."
                )
            with mic as source:
                sample = recognizer.record(source, duration=0.4)
            raw = sample.get_raw_data()
            rms = audioop.rms(raw, 2) if raw else 0
            if DEBUG_HEARING:
                _diag(f"Mic RMS sample: {rms}")
            return

        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=AMBIENT_CALIBRATION_SECONDS)
            if DEBUG_HEARING:
                _diag(
                    "Recognizer calibrated: "
                    f"dynamic={recognizer.dynamic_energy_threshold}, "
                    f"energy_threshold={int(getattr(recognizer, 'energy_threshold', 0))}."
                )

            # Quick signal check: record a short sample and log its RMS.
            # Helps detect when we've bound to a dead/loopback device.
            sample = recognizer.record(source, duration=0.4)
            raw = sample.get_raw_data()
            rms = audioop.rms(raw, 2) if raw else 0
            if DEBUG_HEARING:
                _diag(f"Mic RMS sample: {rms}")
    except Exception as exc:
        _diag(f"Ambient calibration failed ({exc!s}). Using defaults.")


def _transcribe(recognizer: sr.Recognizer, audio: sr.AudioData) -> str:
    if bridge.available:
        try:
            text = bridge.transcribe_wav(audio.get_wav_data())
            if text:
                if DEBUG_HEARING:
                    _diag("STT backend: openai")
                return text
        except Exception as exc:
            _diag(f"OpenAI transcription failed ({exc!s}); falling back to Google.")

    try:
        if DEBUG_HEARING:
            _diag("STT backend: google")
        return recognizer.recognize_google(audio, language=GOOGLE_STT_LANGUAGE)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as exc:
        _diag(f"Online speech-recognition unreachable ({exc!s}).")
        return ""
    except Exception as exc:
        _diag(f"Speech recognition error ({exc!s}).")
        return ""


def normalize_query(query: str) -> str:
    if not query:
        return query
    if bridge.available:
        try:
            return bridge.normalize_to_english(query).lower()
        except Exception:
            return query.lower()
    return query.lower()


def extract_step_count(query: str) -> int:
    match = re.search(r"\b(\d+)\b", query)
    if match:
        return max(1, int(match.group(1)))
    words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    for word, value in words.items():
        if f" {word} " in f" {query} ":
            return value
    return 1


def tell_time() -> str:
    return datetime.datetime.now().strftime("The time is %I:%M %p")


def today_date() -> str:
    return datetime.datetime.now().strftime("Today is %d %B %Y")


def weather_details(query: str) -> str:
    city = OPENWEATHER_DEFAULT_CITY
    match = re.search(r"(?:weather in|weather of|temperature in|temperature of)\s+([a-zA-Z ]+)", query)
    if match:
        candidate = match.group(1).strip()
        if candidate:
            city = candidate.title()

    if not OPENWEATHER_API_KEY:
        return (
            "I can check weather once OPENWEATHER_API_KEY is configured. "
            f"For now, I only know you asked about {city}."
        )

    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        temperature = round(float(data["main"]["temp"]), 1)
        description = data["weather"][0]["description"]
        return f"The temperature in {city} is {temperature} degrees Celsius and the weather is {description}."
    except Exception:
        return f"I could not fetch the weather for {city} right now."


def currently_present() -> str:
    people = read_text(LOG_FILES["current_people"], "none")
    return people or "none"


def handle_quick_command(raw_query: str, normalized_query: str) -> bool:
    if normalized_query in {"anushka", "hey anushka", "okay anushka", "ok anushka", "friday", "edith", "jarvis"}:
        reply = localized_reply(raw_query, "Yes? I am here.")
        speakAndGest(reply)
        log_reply(reply)
        add_history(raw_query, reply)
        return True

    if ListCheck(["turn off", "turn it off", "switch off", "go to sleep", "shutdown", "shut down", "goodbye", "good bye", "bye anushka", "bye anooshka"], normalized_query):
        global _shutdown_requested
        reply = localized_reply(raw_query, "Goodbye. Shutting the system down now.")
        speakAndGest(reply)
        log_reply(reply)
        add_history(raw_query, reply)
        append_message(CONTROL_FILES["boss"], "-1")
        _shutdown_requested = True
        return True

    if ListCheck(["give me your hand", "shake hand", "shake hands"], normalized_query):
        writeToHaath("3")
        reply = localized_reply(raw_query, "Sure. A gentle handshake is appreciated.")
        speakAndGest(reply)
        log_reply(reply)
        add_history(raw_query, reply)
        return True

    if ListCheck(["move", "turn"], normalized_query) and ListCheck(["forward", "ahead", "left", "right", "back", "reverse", "behind"], normalized_query):
        if "left" in normalized_query:
            writeToRolls("l@3")
        elif "right" in normalized_query:
            writeToRolls("r@3")
        elif "forward" in normalized_query or "ahead" in normalized_query:
            writeToRolls(f"f@{extract_step_count(normalized_query)}")
        else:
            writeToRolls(f"b@{extract_step_count(normalized_query)}")
        reply = localized_reply(raw_query, "Moving as requested.")
        speakAndGest(reply)
        log_reply(reply)
        add_history(raw_query, reply)
        return True

    if "follow me" in normalized_query:
        append_message(CONTROL_FILES["vision"], "4")
        reply = localized_reply(raw_query, "Follow mode is now active.")
        speakAndGest(reply)
        log_reply(reply)
        add_history(raw_query, reply)
        return True

    if ListCheck(["off follow", "stop following", "stay where you are", "stay right here"], normalized_query):
        append_message(CONTROL_FILES["vision"], "1")
        reply = localized_reply(raw_query, "Okay. I will stay here.")
        speakAndGest(reply)
        log_reply(reply)
        add_history(raw_query, reply)
        return True

    if ListCheck(["remember them", "remember him", "remember her"], normalized_query):
        append_message(CONTROL_FILES["vision"], "2")
        reply = localized_reply(raw_query, "Understood. I will try to remember them.")
        speakAndGest(reply)
        log_reply(reply)
        add_history(raw_query, reply)
        return True

    if ListCheck(["who am i", "do you know who i am"], normalized_query):
        people = currently_present()
        if people.lower() != "none":
            reply = localized_reply(raw_query, f"My memory tells me you are {people}.")
        else:
            reply = localized_reply(raw_query, "I am not certain yet. Please allow me a little more time to learn faces better.")
        speakAndGest(reply)
        log_reply(reply)
        add_history(raw_query, reply)
        return True

    if ListCheck(["what time", "tell me the time"], normalized_query):
        reply = localized_reply(raw_query, tell_time())
        speakAndGest(reply)
        log_reply(reply)
        add_history(raw_query, reply)
        return True

    if ListCheck(["what is today's date", "date today", "today date"], normalized_query):
        reply = localized_reply(raw_query, today_date())
        speakAndGest(reply)
        log_reply(reply)
        add_history(raw_query, reply)
        return True

    if "weather" in normalized_query or "temperature" in normalized_query:
        reply = localized_reply(raw_query, weather_details(normalized_query))
        speakAndGest(reply)
        log_reply(reply)
        add_history(raw_query, reply)
        return True

    if ListCheck(["make a chuckle", "chuckle"], normalized_query):
        play_resource("Sounds/chuckle.mp3")
        writeToEye("12")
        return True

    if ListCheck(["whistle", "make a whistle"], normalized_query):
        play_resource("Sounds/whistle.mp3")
        return True

    if ListCheck(["yawn", "make a yawn"], normalized_query):
        writeToEye("5")
        play_resource("Sounds/yawn.mp3")
        return True

    prerecorded = {
        "tell me about yourself": "About.wav",
        "ask her to tell about yourself": "About.wav",
        "ask her to tell about yourselves": "About.wav",
        "what do you think about india": "Bharat.wav",
    }
    for phrase, asset in prerecorded.items():
        if phrase in normalized_query:
            if play_resource(asset):
                return True

    return False


def reply_from_ai(raw_query: str) -> str:
    if not bridge.available:
        raise OpenAIUnavailableError("OPENAI_API_KEY is not configured.")
    return bridge.respond(
        user_query=raw_query,
        conversation_history=conversation_history,
        knowledge=_KNOWLEDGE,
        currently_present=currently_present(),
    )


def _read_pending_mode(reader, current_mode: str) -> str:
    """Drain any queued control messages, returning the latest mode."""
    latest = current_mode
    while True:
        incoming = read_available(reader)
        if not incoming:
            return latest
        latest = incoming


def main() -> None:
    global _KNOWLEDGE
    signal.signal(signal.SIGINT, _raise_shutdown)
    signal.signal(signal.SIGTERM, _raise_shutdown)

    _KNOWLEDGE = _load_knowledge_once()

    selection = microphone_selection()
    _diag(f"Microphone: {selection.name} ({selection.reason}).")

    recognizer = _build_recognizer()
    mic: sr.Microphone | None = None
    mic_failure_count = 0
    last_mic_failure_announced = False

    try:
        mic = sr.Microphone(device_index=selection.index)
        _calibrate(recognizer, mic)
    except Exception as exc:
        _diag(f"Could not open microphone ({exc!s}). Hearing will idle in simulation mode until a mic is available.")
        mic = None

    append_message(STATUS_FILES["hear"], "1")
    if HEARING_STARTUP_SPEAK:
        try:
            speak("Hearing systems are now active.")
        except Exception:
            pass

    reader = open_reader(CONTROL_FILES["hear"])
    mode = "1"
    previous_mode = mode
    last_listen_diag = 0.0

    try:
        while True:
            if _shutdown_requested:
                break

            new_mode = _read_pending_mode(reader, mode)
            previous_mode = mode
            mode = new_mode

            if mode == "-1":
                break
            if mode == "0":
                if previous_mode != "0":
                    append_message(CONTROL_FILES["hear_com"], "1")
                time.sleep(0.1)
                continue

            if mic is None:
                # Without a working mic we can do nothing useful; idle and announce once.
                if not last_mic_failure_announced:
                    _diag("Hearing is idle: no usable microphone is currently available.")
                    last_mic_failure_announced = True
                time.sleep(0.5)
                continue

            try:
                writeToEye("6")
                if DEBUG_HEARING and (time.time() - last_listen_diag) > 5.0:
                    _diag(f"Listening... (energy_threshold={int(getattr(recognizer, 'energy_threshold', 0))})")
                    last_listen_diag = time.time()
                with mic as source:
                    audio = recognizer.listen(
                        source,
                        timeout=LISTEN_TIMEOUT_SECONDS,
                        phrase_time_limit=PHRASE_TIME_LIMIT_SECONDS,
                    )
                # Visual blink: signals end-of-speech detected, transcription begins.
                writeToEye("10")
                if DEBUG_HEARING:
                    _diag("Captured audio; transcribing...")
            except sr.WaitTimeoutError:
                if DEBUG_HEARING:
                    try:
                        with mic as source:
                            sample = recognizer.record(source, duration=0.35)
                        raw = sample.get_raw_data()
                        rms = audioop.rms(raw, 2) if raw else 0
                        _diag(f"Listen timeout (RMS={rms})")
                    except Exception as exc:
                        _diag(f"Listen timeout (RMS unavailable: {exc!s})")
                continue
            except OSError as exc:
                mic_failure_count += 1
                _diag(f"Microphone read failed ({exc!s}); attempt {mic_failure_count}.")
                if mic_failure_count >= 3:
                    _diag("Microphone has failed repeatedly. Re-resolving device.")
                    new_selection = microphone_selection(refresh=True)
                    try:
                        mic = sr.Microphone(device_index=new_selection.index)
                        _calibrate(recognizer, mic)
                        _diag(f"Microphone re-bound to: {new_selection.name}.")
                        mic_failure_count = 0
                        last_mic_failure_announced = False
                    except Exception as inner:
                        _diag(f"Re-bind failed ({inner!s}). Idling.")
                        mic = None
                        mic_failure_count = 0
                time.sleep(min(2.0, 0.2 * mic_failure_count))
                continue
            except Exception as exc:
                _diag(f"Unexpected listen error ({exc!s}).")
                time.sleep(0.5)
                continue
            else:
                mic_failure_count = 0

            query = _transcribe(recognizer, audio).strip()
            if not query:
                continue

            if DEBUG_HEARING:
                _diag(f"Heard: {query[:200]}")

            log_query(query)
            normalized = normalize_query(query)

            if DEBUG_HEARING:
                _diag(f"Normalized: {normalized[:200]}")

            if handle_quick_command(query, normalized):
                continue

            offline_found, offline_reply, offline_source = offline_qa.match_query(normalized)
            if offline_found:
                _diag(f"Offline Q&A hit ({offline_source}).")
                try:
                    speakAndGest(offline_reply)
                except Exception as exc:
                    _diag(f"Speech output failed ({exc!s}).")
                log_reply(offline_reply)
                add_history(query, offline_reply)
                continue

            try:
                reply = reply_from_ai(query)
            except OpenAIUnavailableError:
                reply = OfflineChatbot(normalized) or offline_qa.generic_fallback()
            except Exception as exc:
                _diag(f"Chat reply failed ({exc!s}).")
                reply = "I am sorry, but I had trouble thinking through that just now."

            if not reply:
                continue

            try:
                speakAndGest(reply)
            except Exception as exc:
                _diag(f"Speech output failed ({exc!s}).")
            log_reply(reply)
            add_history(query, reply)
    finally:
        try:
            reader.close()
        except Exception:
            pass
        append_message(STATUS_FILES["hear"], "2")


if __name__ == "__main__":
    main()
