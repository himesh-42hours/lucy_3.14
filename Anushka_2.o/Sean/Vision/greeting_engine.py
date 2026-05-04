"""Vision-first greeting engine.

Encapsulates face encoding, matching, and per-session greeting bookkeeping
so the orchestrator can fire a personalised greeting BEFORE the hearing
module is up — and so vision_controller.py can route greetings through a
single place.

Heavy dependencies (cv2, face_recognition, numpy) are imported lazily; the
module is importable on machines without them so the orchestrator can still
run in smoke-test or sim mode.
"""

from __future__ import annotations

import datetime
import os
import sys
import time
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)


FACES_DIR = SEAN_ROOT / "Vision" / "faces"
LAST_SEEN_FILE = SEAN_ROOT / "Vision" / "lastSeenMe.txt"
CURRENTLY_PRESENT_FILE = SEAN_ROOT / "Vision" / "currentlyPresent.txt"

FACE_DISTANCE_THRESHOLD = 0.48


def _diag(message: str) -> None:
    try:
        sys.stderr.write(f"[vision/greeting] {message}\n")
        sys.stderr.flush()
    except Exception:
        pass


def _greeting_for(name: str) -> str:
    """Persona-flavoured greeting line for a known face."""
    if not name:
        return "Hello there. Nice to meet you."

    lowered = name.lower()
    if "father" in lowered or "himesh" in lowered:
        return "Hello Himesh ji. Always a delight to see you."
    if "manoj" in lowered:
        return "Pruhnaum sir. Nice to meet you Doctor Manoj Goyal."
    if "sachin" in lowered:
        return "Hello sir. Nice to meet you Mr. Sachin Tyagi."

    pretty = name.replace("_", " ").strip()
    hour = datetime.datetime.now().hour
    if 6 < hour < 12:
        return f"A very good morning, {pretty}. It is wonderful to see you."
    if 12 <= hour < 16:
        return f"A very good afternoon, {pretty}. It is wonderful to see you."
    return f"A very good evening, {pretty}. It is wonderful to see you."


def _generic_unknown_greeting() -> str:
    return "Hello there. Nice to meet you."


class GreetingEngine:
    """Loads known faces once and decides who, if anyone, to greet.

    Greeting state is per-session (in-memory). The class is safe to
    instantiate even when face-recognition libs are missing — it then runs
    in degraded mode where ``detect_and_greet`` returns ``None``.
    """

    def __init__(self, faces_dir: Path = FACES_DIR) -> None:
        self.faces_dir = faces_dir
        self._known_encodings: list = []
        self._known_names: list[str] = []
        self._already_greeted: set[str] = set()
        self._last_greeting_at: dict[str, float] = {}
        self._cv2 = None
        self._face_recognition = None
        self._np = None
        self._ready = False
        self._load()

    # ------------------------------------------------------------------
    # Loading & encoding
    # ------------------------------------------------------------------
    def _load(self) -> None:
        try:
            import cv2  # type: ignore
            import face_recognition  # type: ignore
            import numpy as np  # type: ignore
        except Exception as exc:
            _diag(f"Vision libs unavailable; greeting engine in degraded mode ({exc!s}).")
            return

        self._cv2 = cv2
        self._face_recognition = face_recognition
        self._np = np

        if not self.faces_dir.exists():
            _diag(f"Faces directory missing: {self.faces_dir}.")
            return

        for entry in sorted(os.listdir(self.faces_dir)):
            full = self.faces_dir / entry
            if not full.is_file():
                continue
            try:
                img = cv2.imread(str(full))
                if img is None:
                    continue
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                encodings = face_recognition.face_encodings(img_rgb)
                if not encodings:
                    continue
                self._known_encodings.append(encodings[0])
                self._known_names.append(os.path.splitext(entry)[0])
            except Exception as exc:
                _diag(f"Failed to encode {entry} ({exc!s}).")

        self._ready = bool(self._known_encodings)
        _diag(f"Loaded {len(self._known_names)} known face(s); ready={self._ready}.")

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def known_names(self) -> list[str]:
        return list(self._known_names)

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------
    def match_encoding(self, encoding) -> Optional[str]:
        """Return the known person's name for ``encoding``, or None."""
        if not self._ready or self._face_recognition is None or self._np is None:
            return None
        try:
            distances = self._face_recognition.face_distance(self._known_encodings, encoding)
            best = int(self._np.argmin(distances))
            if distances[best] <= FACE_DISTANCE_THRESHOLD:
                return self._known_names[best]
        except Exception as exc:
            _diag(f"match_encoding failed ({exc!s}).")
        return None

    # ------------------------------------------------------------------
    # Greetings
    # ------------------------------------------------------------------
    def should_greet(self, identifier: str, cooldown_seconds: float = 600.0) -> bool:
        """One greeting per face per session; soft cooldown for repeats."""
        if not identifier:
            return False
        if identifier in self._already_greeted:
            last = self._last_greeting_at.get(identifier, 0.0)
            return (time.time() - last) > cooldown_seconds
        return True

    def mark_greeted(self, identifier: str) -> None:
        if not identifier:
            return
        self._already_greeted.add(identifier)
        self._last_greeting_at[identifier] = time.time()

    def greet_person(self, identifier: Optional[str]) -> tuple[str, str]:
        """Resolve a greeting line and the canonical display name."""
        if identifier:
            return identifier, _greeting_for(identifier)
        return "stranger", _generic_unknown_greeting()

    # ------------------------------------------------------------------
    # End-to-end helpers
    # ------------------------------------------------------------------
    def detect_in_frame(self, frame) -> Optional[str]:
        """Run face detection on a BGR frame; return matched name or None.

        Returns ``None`` if no face, or a face matched to ``"unknown"``.
        """
        if not self._ready or self._cv2 is None or self._face_recognition is None:
            return None
        try:
            rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
            encodings = self._face_recognition.face_encodings(rgb)
            if not encodings:
                return None
            for encoding in encodings:
                name = self.match_encoding(encoding)
                if name:
                    return name
            return "unknown"
        except Exception as exc:
            _diag(f"detect_in_frame failed ({exc!s}).")
            return None

    def greet_if_person_in_frame(
        self,
        camera_index: int = 0,
        max_attempts: int = 5,
        attempt_delay: float = 0.4,
        speak_fn=None,
    ) -> Optional[tuple[str, str]]:
        """Try briefly to spot a face on the given camera and greet.

        Returns ``(name, greeting_text)`` if a greeting fired, else ``None``.
        Designed to be called by the orchestrator BEFORE hearing starts.
        """
        if not self._ready or self._cv2 is None:
            return None

        cap = None
        try:
            cap = self._cv2.VideoCapture(camera_index)
            if not cap or not cap.isOpened():
                _diag(f"Camera {camera_index} did not open; skipping early greeting.")
                return None

            for attempt in range(max_attempts):
                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(attempt_delay)
                    continue
                identifier = self.detect_in_frame(frame)
                if identifier is None:
                    time.sleep(attempt_delay)
                    continue
                if identifier == "unknown":
                    if not self.should_greet("__unknown__"):
                        return None
                    name, line = self.greet_person(None)
                    self.mark_greeted("__unknown__")
                else:
                    if not self.should_greet(identifier):
                        return None
                    name, line = self.greet_person(identifier)
                    self.mark_greeted(identifier)

                try:
                    CURRENTLY_PRESENT_FILE.write_text(
                        identifier if identifier != "unknown" else "none",
                        encoding="utf-8",
                    )
                except Exception:
                    pass

                if speak_fn is not None:
                    try:
                        speak_fn(line)
                    except Exception as exc:
                        _diag(f"speak_fn failed during greeting ({exc!s}).")

                return name, line
            return None
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass


_DEFAULT_ENGINE: GreetingEngine | None = None


def get_default_engine() -> GreetingEngine:
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = GreetingEngine()
    return _DEFAULT_ENGINE


def greet_if_person_in_frame(
    camera_index: int = 0,
    speak_fn=None,
    max_attempts: int = 5,
) -> Optional[tuple[str, str]]:
    """Module-level convenience wrapper around the default engine."""
    return get_default_engine().greet_if_person_in_frame(
        camera_index=camera_index,
        max_attempts=max_attempts,
        speak_fn=speak_fn,
    )


if __name__ == "__main__":
    engine = GreetingEngine()
    print(f"ready={engine.ready}, known={engine.known_names}")
