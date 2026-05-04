from __future__ import annotations

import sys
import time
from pathlib import Path

import serial


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from anushka_runtime.config import CONTROL_FILES, GARDAN_PORT, STATUS_FILES
from anushka_runtime.ipc import append_message, open_reader, read_available


def main() -> None:
    neck = None
    if GARDAN_PORT:
        try:
            neck = serial.Serial(GARDAN_PORT, baudrate=9600, timeout=2)
        except Exception:
            append_message(STATUS_FILES["gardan"], f"Neck serial port {GARDAN_PORT} is unavailable. Running in simulation mode.")

    reader = open_reader(CONTROL_FILES["gardan"])
    append_message(STATUS_FILES["gardan"], "1")

    try:
        while True:
            command = read_available(reader)
            if not command:
                time.sleep(0.1)
                continue
            if command == "-1":
                break
            payload = "270" if command == "-2" else command
            if neck:
                try:
                    neck.write(payload.encode("utf-8"))
                except Exception:
                    append_message(STATUS_FILES["gardan"], "Neck mechanism lost serial connectivity and is continuing in simulation mode.")
                    neck = None
    finally:
        if neck:
            neck.close()
        reader.close()


if __name__ == "__main__":
    main()
