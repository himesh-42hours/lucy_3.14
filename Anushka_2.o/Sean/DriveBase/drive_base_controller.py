from __future__ import annotations

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

from anushka_runtime.config import CONTROL_FILES, ROLLS_PORT, STATUS_FILES
from anushka_runtime.ipc import append_message, open_reader, read_available


def main() -> None:
    rolls = None
    if ROLLS_PORT:
        try:
            rolls = serial.Serial(ROLLS_PORT, baudrate=9600, timeout=2)
        except Exception:
            append_message(STATUS_FILES["rolls"], f"Rolls serial port {ROLLS_PORT} is unavailable. Running in simulation mode.")

    append_message(STATUS_FILES["rolls"], "1")
    reader = open_reader(CONTROL_FILES["rolls"])
    try:
        while True:
            command = read_available(reader)
            if not command:
                time.sleep(0.1)
                continue
            if command == "-1":
                break
            if rolls:
                try:
                    rolls.write(command.encode("utf-8"))
                except Exception:
                    append_message(STATUS_FILES["rolls"], "Moving base lost serial connectivity and is continuing in simulation mode.")
                    rolls = None
    finally:
        if rolls:
            rolls.close()
        reader.close()


if __name__ == "__main__":
    main()
