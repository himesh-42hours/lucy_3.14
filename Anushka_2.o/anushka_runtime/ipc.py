from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable, TextIO

from .config import CONTROL_FILES, LOG_FILES, STATUS_FILES


def ensure_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return path


def write_text(path: Path, text: str) -> None:
    ensure_file(path)
    path.write_text(text, encoding="utf-8")


def append_message(path: Path, message: str) -> None:
    ensure_file(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{message.strip()}\n")


def open_reader(path: Path) -> TextIO:
    ensure_file(path)
    return path.open("r", encoding="utf-8")


def read_available(handle: TextIO) -> str:
    line = handle.readline()
    if not line:
        return ""
    return line.strip()


def read_next_message(handle: TextIO, poll_interval: float = 0.1) -> str:
    while True:
        line = read_available(handle)
        if line:
            return line
        time.sleep(poll_interval)


def ensure_runtime_tree() -> None:
    for path in list(CONTROL_FILES.values()) + list(STATUS_FILES.values()) + list(LOG_FILES.values()):
        ensure_file(path)


def reset_runtime_state() -> None:
    ensure_runtime_tree()
    for path in CONTROL_FILES.values():
        write_text(path, "")
    for path in STATUS_FILES.values():
        write_text(path, "")
    write_text(LOG_FILES["conversation"], "")


def _iter_paths(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        yield ensure_file(path)
