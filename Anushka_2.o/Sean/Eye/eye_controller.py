from __future__ import annotations

import random
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import serial

from anushka_runtime.config import CONTROL_FILES, EYE_PORT, STATUS_FILES
from anushka_runtime.ipc import append_message, open_reader, read_available


def main() -> None:
    eye = None
    if EYE_PORT:
        try:
            eye = serial.Serial(EYE_PORT, baudrate=9600, timeout=2)
        except Exception:
            append_message(STATUS_FILES["eye"], f"Eye serial port {EYE_PORT} is unavailable. Running in simulation mode.")

    reader = open_reader(CONTROL_FILES["eye"])
    time.sleep(1)
    if eye:
        try:
            eye.write(b"0")
        except Exception:
            pass

    append_message(STATUS_FILES["eye"], "1")
    try:
        while True:
            command = read_available(reader)
            if not command:
                time.sleep(0.1)
                continue
            if command == "-1":
                break
            if command == "6":
                command = str(random.randint(7, 15))
            if eye:
                try:
                    eye.write(command.encode("utf-8"))
                except Exception:
                    append_message(STATUS_FILES["eye"], "Eye mechanism lost serial connectivity and is continuing in simulation mode.")
                    eye = None
    finally:
        if eye:
            eye.close()
        reader.close()


if __name__ == "__main__":
    main()
