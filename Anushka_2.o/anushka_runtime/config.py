from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
SEAN_ROOT = REPO_ROOT / "Sean"
RESOURCES_DIR = SEAN_ROOT / "Resources"

load_dotenv(REPO_ROOT / ".env")


def _bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: Optional[int]) -> Optional[int]:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def camera_source_from_env(name: str, default: int | str = 0) -> int | str:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    raw_value = raw_value.strip()
    try:
        return int(raw_value)
    except ValueError:
        return raw_value


def _float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def serial_port_from_env(name: str, default: Optional[str | int]) -> Optional[str]:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        raw_value = "" if default is None else str(default)
    raw_value = raw_value.strip()
    if raw_value == "":
        return None
    if raw_value.isdigit():
        return f"COM{raw_value}"
    return raw_value


def _serial_port_candidates():
    try:
        from serial.tools import list_ports

        return list(list_ports.comports())
    except Exception:
        return []


def _serial_value_matches_port(value: str, port) -> bool:
    needle = value.strip().lower()
    if not needle:
        return False

    fields = [
        getattr(port, "device", ""),
        getattr(port, "description", ""),
        getattr(port, "hwid", ""),
        getattr(port, "manufacturer", ""),
        getattr(port, "product", ""),
        getattr(port, "serial_number", ""),
        getattr(port, "location", ""),
    ]
    for field in fields:
        text = str(field).strip().lower()
        if not text:
            continue
        if needle == text or needle in text:
            return True
    return False


def serial_port_from_id_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Resolve a stable USB identifier to a concrete serial device path.

    Accepts either a full device path (for example ``/dev/serial/by-id/...``),
    a COM name, or a lookup token such as a serial number / description
    fragment. The lookup token is matched against the current serial devices
    reported by pyserial.
    """
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        raw_value = "" if default is None else default
    raw_value = raw_value.strip()
    if raw_value == "":
        return None
    if raw_value.isdigit():
        return f"COM{raw_value}"
    if raw_value.startswith("/") or raw_value.upper().startswith("COM"):
        return raw_value

    for port in _serial_port_candidates():
        if _serial_value_matches_port(raw_value, port):
            return port.device

    return None


def path_for(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


CONTROL_FILES = {
    "boss": path_for("Sean", "BOSS", "bossWS.txt"),
    "speech": path_for("Sean", "Speech", "speechWS.txt"),
    "speech_command": path_for("Sean", "Speech", "speechCF.txt"),
    "haath": path_for("Sean", "Arms", "armsWS.txt"),
    "hear": path_for("Sean", "Hearing", "hearWS.txt"),
    "hear_com": path_for("Sean", "Hearing", "hearCom.txt"),
    "eye": path_for("Sean", "Eye", "eyeWS.txt"),
    "rolls": path_for("Sean", "DriveBase", "driveBaseWS.txt"),
    "vision": path_for("Sean", "Vision", "visionWS.txt"),
    "jaw": path_for("Sean", "Jaw", "jawWS.txt"),
    "monitor": path_for("Sean", "Monitor", "monitorWS.txt"),
    "heartbeat": path_for("Sean", "Heartbeat", "heartbeatWS.txt"),
    "gardan": path_for("Neck", "neckWS.txt"),
    "auxmega": path_for("Sean", "AuxMega", "auxmegaWS.txt"),
}

STATUS_FILES = {
    "haath": path_for("Sean", "Arms", "armsEF.txt"),
    "speech": path_for("Sean", "Speech", "speechEF.txt"),
    "hear": path_for("Sean", "Hearing", "hearEF.txt"),
    "eye": path_for("Sean", "Eye", "eyeEF.txt"),
    "rolls": path_for("Sean", "DriveBase", "driveBaseEF.txt"),
    "vision": path_for("Sean", "Vision", "visionEF.txt"),
    "jaw": path_for("Sean", "Jaw", "jawEF.txt"),
    "monitor": path_for("Sean", "Monitor", "monitorEF.txt"),
    "heartbeat": path_for("Sean", "Heartbeat", "heartbeatEF.txt"),
    "gardan": path_for("Neck", "neckEF.txt"),
    "auxmega": path_for("Sean", "AuxMega", "auxmegaEF.txt"),
}

LOG_FILES = {
    "conversation": path_for("Sean", "Monitor", "Now.txt"),
    "test": path_for("Sean", "Tests", "testLog.txt"),
    "current_people": path_for("Sean", "Vision", "currentlyPresent.txt"),
    "last_seen": path_for("Sean", "Vision", "lastSeenMe.txt"),
    "knowledge": path_for("Sean", "Brain", "Database", "knowledge_log.txt"),
    "persona": path_for("Sean", "Brain", "Database", "chat_log_female.txt"),
}


def module_script(name: str) -> Path:
    scripts = {
        "heartbeat": path_for("Sean", "Heartbeat", "heartbeat_controller.py"),
        "monitor": path_for("Sean", "Monitor", "monitor_controller.py"),
        "haath": path_for("Sean", "Arms", "arms_controller.py"),
        "rolls": path_for("Sean", "DriveBase", "drive_base_controller.py"),
        "auxmega": path_for("Sean", "AuxMega", "auxmega_controller.py"),
        "hear": path_for("Sean", "Hearing", "hearing_controller.py"),
        "vision": path_for("Sean", "Vision", "vision_controller.py"),
    }
    return scripts[name]


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe").strip() or "gpt-4o-mini-transcribe"
OPENAI_TRANSCRIBE_LANGUAGE = os.getenv("OPENAI_TRANSCRIBE_LANGUAGE", "").strip()

# Control reply language behavior.
# - auto: keep legacy behavior (reply in the same language/script as the user's message)
# - en: always reply in English
# - hi: always reply in Hindi
# - hinglish: Hindi in Latin script (easier for mixed audiences)
REPLY_LANGUAGE = os.getenv("ANUSHKA_REPLY_LANGUAGE", "auto").strip().lower() or "auto"

# When REPLY_LANGUAGE=auto, allow a second-pass "mirror language" rewrite for quick, canned replies.
# If transcription is noisy, this rewrite can create random scripts, so you may want it off.
ENABLE_LANGUAGE_MIRROR = _bool_env("ANUSHKA_ENABLE_LANGUAGE_MIRROR", True)

# Used only for the Google SpeechRecognition fallback (when OpenAI transcription is unavailable).
GOOGLE_STT_LANGUAGE = os.getenv("ANUSHKA_GOOGLE_STT_LANGUAGE", "en-IN").strip() or "en-IN"

DEBUG_HEARING = _bool_env("ANUSHKA_DEBUG_HEARING", False)
TTS_ENGINE = os.getenv("ANUSHKA_TTS_ENGINE", "pyttsx3").strip().lower() or "pyttsx3"
TTS_MODEL = os.getenv("ANUSHKA_TTS_MODEL", "gpt-4o-mini-tts").strip() or "gpt-4o-mini-tts"
TTS_VOICE = os.getenv("ANUSHKA_TTS_VOICE", "nova").strip() or "nova"
TTS_INSTRUCTIONS = os.getenv(
    "ANUSHKA_TTS_INSTRUCTIONS",
    "Speak warmly, naturally, and conversationally, like a friendly humanoid robot talking to visitors.",
).strip()
TTS_SPEED = _float_env("ANUSHKA_TTS_SPEED", 0.95)
MIC_DEVICE_INDEX = _int_env("ANUSHKA_MIC_DEVICE_INDEX", None)
MIC_NAME_HINT = os.getenv("ANUSHKA_MIC_NAME_HINT", "ReSpeaker").strip()
CAMERA_SOURCE = camera_source_from_env("ANUSHKA_CAMERA_SOURCE", 0)
CAMERA_INDEX = CAMERA_SOURCE if isinstance(CAMERA_SOURCE, int) else 0
CAMERA_NAME_HINT = os.getenv("ANUSHKA_CAMERA_NAME_HINT", "Kreo").strip()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()
OPENWEATHER_DEFAULT_CITY = os.getenv("OPENWEATHER_DEFAULT_CITY", "Ghaziabad").strip() or "Ghaziabad"

ENABLE_VISION = _bool_env("ANUSHKA_ENABLE_VISION", False)
ENABLE_MONITORING = _bool_env("ANUSHKA_ENABLE_MONITORING", True)
ENABLE_EARLY_GREETING = _bool_env("ANUSHKA_ENABLE_EARLY_GREETING", False)

MONITOR_URL = os.getenv("ANUSHKA_MONITOR_URL", "http://10.21.69.5:3000").rstrip("/")

LEFT_ARM_MEGA_PORT = (
    serial_port_from_id_env("ANUSHKA_LEFT_ARM_MEGA_ID")
    or serial_port_from_env("ANUSHKA_LEFT_ARM_MEGA_PORT", os.getenv("ANUSHKA_LEFT_HAND_PORT", ""))
)
RIGHT_ARM_MEGA_PORT = (
    serial_port_from_id_env("ANUSHKA_RIGHT_ARM_MEGA_ID")
    or serial_port_from_env("ANUSHKA_RIGHT_ARM_MEGA_PORT", os.getenv("ANUSHKA_RIGHT_HAND_PORT", ""))
)

# The first Mega handles the head: neck, jaw, eyes, eyelids.
# `ANUSHKA_AUX_MEGA_PORT` is kept as a legacy alias so older .env files still work.
HEAD_MEGA_PORT = (
    serial_port_from_id_env("ANUSHKA_HEAD_MEGA_ID")
    or serial_port_from_env("ANUSHKA_HEAD_MEGA_PORT", os.getenv("ANUSHKA_AUX_MEGA_PORT", ""))
)

# The fourth Mega handles the mobile base.
BASE_MEGA_PORT = (
    serial_port_from_id_env("ANUSHKA_BASE_MEGA_ID")
    or serial_port_from_env("ANUSHKA_BASE_MEGA_PORT", os.getenv("ANUSHKA_ROLLS_PORT", ""))
)

# Legacy alias kept for older modules and docs.
AUX_MEGA_PORT = HEAD_MEGA_PORT

# Legacy aliases kept for compatibility with older modules.
LEFT_HAND_PORT = LEFT_ARM_MEGA_PORT
RIGHT_HAND_PORT = RIGHT_ARM_MEGA_PORT
PALM_PORT = None
EYE_PORT = HEAD_MEGA_PORT
JAW_PORT = HEAD_MEGA_PORT
ROLLS_PORT = BASE_MEGA_PORT
GARDAN_PORT = HEAD_MEGA_PORT
