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

from anushka_runtime.config import BASE_MEGA_PORT, CONTROL_FILES, STATUS_FILES
from anushka_runtime.ipc import append_message, open_reader, read_available


DEFAULT_BASE_SPEED = 140


def _parse_seconds(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def main() -> None:
    base = None
    if BASE_MEGA_PORT:
        try:
            base = serial.Serial(BASE_MEGA_PORT, baudrate=9600, timeout=2)
        except Exception:
            append_message(STATUS_FILES["rolls"], f"Base serial port {BASE_MEGA_PORT} is unavailable. Running in simulation mode.")

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

            cmd = command.strip()
            upper = cmd.upper()

            if upper.startswith("BASE:") or upper.startswith("GESTURE:") or upper == "STOP":
                payload = upper
            else:
                if "@" not in cmd:
                    continue
                direction = cmd[0].upper()
                seconds = _parse_seconds(cmd.split("@", 1)[1])
                if seconds is None:
                    continue
                if direction not in {"F", "B", "L", "R"}:
                    continue
                duration_ms = max(0, int(seconds * 1000))
                payload = f"BASE:{direction},{DEFAULT_BASE_SPEED},{duration_ms}"

            if base:
                try:
                    base.write(f"{payload}\n".encode("utf-8"))
                except Exception:
                    append_message(STATUS_FILES["rolls"], "Moving base lost serial connectivity and is continuing in simulation mode.")
                    base = None
    finally:
        if base:
            base.close()
        reader.close()


if __name__ == "__main__":
    main()
