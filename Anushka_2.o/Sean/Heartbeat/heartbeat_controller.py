from __future__ import annotations

import os
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

os.environ.setdefault("SDL_AUDIODRIVER", "pulse")

import pygame

from anushka_runtime.config import CONTROL_FILES, STATUS_FILES, path_for
from anushka_runtime.ipc import append_message, open_reader, read_available


INITIAL_BEAT = path_for("Sean", "Heartbeat", "initialBeat.mp3")
NORMAL_BEAT = path_for("Sean", "Heartbeat", "normalBeat.mp3")

_shutdown_requested = False


def _on_signal(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True


def _diag(message: str) -> None:
    append_message(STATUS_FILES["heartbeat"], message)
    try:
        sys.stderr.write(f"[heartbeat] {message}\n")
        sys.stderr.flush()
    except Exception:
        pass


def play_once(audio_path: Path, watch_shutdown: bool = True) -> None:
    if not audio_path.exists():
        return
    try:
        pygame.mixer.music.load(str(audio_path))
        pygame.mixer.music.play()
        clock = pygame.time.Clock()
        while pygame.mixer.music.get_busy():
            if watch_shutdown and _shutdown_requested:
                pygame.mixer.music.stop()
                return
            clock.tick(30)
    except Exception:
        return


def main() -> None:
    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    audio_ok = True
    try:
        pygame.mixer.init()
    except Exception as exc:
        audio_ok = False
        _diag(f"Audio output for heartbeat is unavailable ({exc!s}). Running silently.")

    if audio_ok:
        play_once(INITIAL_BEAT)
    append_message(STATUS_FILES["heartbeat"], "1")

    if audio_ok:
        try:
            if NORMAL_BEAT.exists():
                pygame.mixer.music.load(str(NORMAL_BEAT))
                pygame.mixer.music.play(-1)
        except Exception as exc:
            _diag(f"Could not start looping heartbeat ({exc!s}).")

    reader = open_reader(CONTROL_FILES["heartbeat"])
    global _shutdown_requested
    try:
        while True:
            if _shutdown_requested:
                break
            command = read_available(reader)
            if not command:
                time.sleep(0.1)
                continue
            if command == "-1":
                _shutdown_requested = True
                break
    finally:
        if audio_ok:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            # Skip the closing fanfare during shutdown so the process exits promptly.
            if not _shutdown_requested:
                play_once(INITIAL_BEAT, watch_shutdown=False)
        append_message(STATUS_FILES["heartbeat"], "2")
        try:
            reader.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
