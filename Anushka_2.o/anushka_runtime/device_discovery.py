from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .config import MIC_DEVICE_INDEX, MIC_NAME_HINT


# Heuristics for unlikely-to-have-a-real-input-mic devices on Linux.
_NEGATIVE_NAME_TOKENS = ("hdmi", "monitor of", "iec958", "spdif")
# Heuristics that often map to a usable input on a laptop.
_POSITIVE_NAME_TOKENS = (
    "pulse",
    "default",
    "pipewire",
    "analog",
    "input",
    "mic",
    "internal",
    "alc",
    "respeaker",
    "usb audio",
    "webcam",
)


@dataclass(frozen=True)
class MicrophoneSelection:
    index: Optional[int]
    name: str
    reason: str


def _list_names() -> List[str]:
    try:
        import speech_recognition as sr

        return list(sr.Microphone.list_microphone_names())
    except Exception:
        return []


def _score(name: str) -> int:
    lowered = name.lower()
    if any(tok in lowered for tok in _NEGATIVE_NAME_TOKENS):
        return -10
    score = 0
    for tok in _POSITIVE_NAME_TOKENS:
        if tok in lowered:
            score += 1
    return score


def _try_open(index: Optional[int]) -> bool:
    """Attempt to open the microphone briefly. Returns True if it worked."""
    try:
        import speech_recognition as sr

        with sr.Microphone(device_index=index):
            return True
    except Exception:
        return False


def _select() -> MicrophoneSelection:
    if MIC_DEVICE_INDEX is not None:
        names = _list_names()
        name = names[MIC_DEVICE_INDEX] if 0 <= MIC_DEVICE_INDEX < len(names) else f"index {MIC_DEVICE_INDEX}"
        return MicrophoneSelection(MIC_DEVICE_INDEX, name, "ANUSHKA_MIC_DEVICE_INDEX env override")

    names = _list_names()

    if MIC_NAME_HINT:
        hint = MIC_NAME_HINT.lower()
        for index, name in enumerate(names):
            if hint in name.lower():
                return MicrophoneSelection(index, name, f"matched ANUSHKA_MIC_NAME_HINT='{MIC_NAME_HINT}'")

    # Try the system default first; this is usually the right answer on a laptop.
    if _try_open(None):
        return MicrophoneSelection(None, "system default", "system default microphone is available")

    # Otherwise score the listed names and pick the best candidate that opens.
    ranked: List[Tuple[int, int, str]] = sorted(
        ((-_score(name), index, name) for index, name in enumerate(names) if _score(name) >= 0),
        key=lambda item: (item[0], item[1]),
    )
    for _, index, name in ranked:
        if _try_open(index):
            return MicrophoneSelection(index, name, "best-scoring available input device")

    return MicrophoneSelection(None, "unavailable", "no working microphone found")


_cached_selection: Optional[MicrophoneSelection] = None


def microphone_selection(refresh: bool = False) -> MicrophoneSelection:
    global _cached_selection
    if refresh or _cached_selection is None:
        _cached_selection = _select()
    return _cached_selection


def resolve_microphone_index() -> Optional[int]:
    return microphone_selection().index
