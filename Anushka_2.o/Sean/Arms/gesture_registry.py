from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class GestureSpec:
    code: str
    name: str
    reply: str
    phrases: tuple[str, ...]


# Keep this registry in sync with `Arms/arms_controller.py`.
# Add a new entry here when you want speech/hearing to recognize a phrase,
# and add the same numeric code to the Arduino/Python gesture executor.
GESTURES: tuple[GestureSpec, ...] = (
    GestureSpec(
        code="12",
        name="salute",
        reply="Certainly. Saluting now.",
        phrases=("salute", "do salute", "give salute"),
    ),
    GestureSpec(
        code="6",
        name="raise_hand",
        reply="Raising my right hand.",
        phrases=("raise hand", "raise your hand", "lift hand", "lift your hand"),
    ),
    GestureSpec(
        code="7",
        name="raise_both_hands",
        reply="Raising both hands.",
        phrases=("raise both hands", "raise both arms", "lift both hands"),
    ),
    GestureSpec(
        code="3",
        name="shake_hand",
        reply="Sure. A gentle handshake is appreciated.",
        phrases=("give me your hand", "shake hand", "shake hands"),
    ),
    GestureSpec(
        code="4",
        name="point_left",
        reply="Pointing to the left.",
        phrases=("point left", "show left", "look to the left"),
    ),
    GestureSpec(
        code="5",
        name="point_right",
        reply="Pointing to the right.",
        phrases=("point right", "show right", "look to the right"),
    ),
    GestureSpec(
        code="15",
        name="thumbs_up",
        reply="Thumbs up.",
        phrases=("thumbs up", "show thumbs up", "all the best"),
    ),
    GestureSpec(
        code="16",
        name="okay",
        reply="Okay.",
        phrases=("make okay sign", "show okay sign", "okay sign"),
    ),
    GestureSpec(
        code="20",
        name="open_arms",
        reply="Opening both arms.",
        phrases=("open your arms", "spread your arms", "open both hands"),
    ),
    GestureSpec(
        code="21",
        name="close_arms",
        reply="Closing both arms.",
        phrases=("close your arms", "close both hands", "fold your hands"),
    ),
    GestureSpec(
        code="30",
        name="call_me",
        reply="Here is the call me gesture.",
        phrases=("call me gesture", "show call me", "give me a call sign"),
    ),
    GestureSpec(
        code="11",
        name="self_point",
        reply="Pointing to myself.",
        phrases=("point at yourself", "point to yourself", "show yourself"),
    ),
)


BY_CODE = {spec.code: spec for spec in GESTURES}
BY_NAME = {spec.name: spec for spec in GESTURES}


def _normalize(text: str) -> str:
    # Replace punctuation with spaces so phrases like "do salute." still match.
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower())
    normalized = re.sub(r"\s+", " ", cleaned).strip()
    return f" {normalized} "


def find_gesture_for_query(query: str) -> GestureSpec | None:
    lowered = _normalize(query)
    for spec in GESTURES:
        for phrase in spec.phrases:
            phrase_norm = re.sub(r"[^a-z0-9]+", " ", phrase.lower())
            phrase_norm = re.sub(r"\s+", " ", phrase_norm).strip()
            if f" {phrase_norm} " in lowered:
                return spec
    return None


def resolve_gesture(token: str) -> GestureSpec | None:
    cleaned = token.strip().lower()
    if not cleaned:
        return None
    if cleaned in BY_CODE:
        return BY_CODE[cleaned]
    return BY_NAME.get(cleaned)
