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

from anushka_runtime.config import CONTROL_FILES, JAW_PORT, STATUS_FILES
from anushka_runtime.ipc import append_message, open_reader, read_available


def main() -> None:
    jaw = None
    if JAW_PORT:
        try:
            jaw = serial.Serial(JAW_PORT, baudrate=9600, timeout=2)
        except Exception:
            append_message(STATUS_FILES["jaw"], f"Jaw serial port {JAW_PORT} is unavailable. Running in simulation mode.")

    reader = open_reader(CONTROL_FILES["jaw"])
    append_message(STATUS_FILES["jaw"], "1")

    try:
        while True:
            command = read_available(reader)
            if not command:
                time.sleep(0.05)
                continue
            if command == "-1":
                break
            if jaw:
                try:
                    jaw.write(command.encode("utf-8"))
                except Exception:
                    append_message(STATUS_FILES["jaw"], "Jaw mechanism lost serial connectivity and is continuing in simulation mode.")
                    jaw = None
    finally:
        if jaw:
            jaw.close()
        reader.close()


if __name__ == "__main__":
    main()
