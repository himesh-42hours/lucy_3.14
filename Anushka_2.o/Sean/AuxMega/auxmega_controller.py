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

from anushka_runtime.config import AUX_MEGA_PORT, CONTROL_FILES, STATUS_FILES
from anushka_runtime.ipc import append_message, open_reader, read_available


PREFIX_BY_CHANNEL = {
    "jaw": "J",
    "eye": "E",
    "gardan": "N",
    "rolls": "R",
}


def _diag(message: str) -> None:
    append_message(STATUS_FILES["auxmega"], message)
    try:
        sys.stderr.write(f"[auxmega] {message}\n")
        sys.stderr.flush()
    except Exception:
        pass


def _open_aux() -> "serial.Serial | None":
    if not AUX_MEGA_PORT:
        _diag("ANUSHKA_AUX_MEGA_PORT is not set. Running in simulation mode.")
        return None
    try:
        return serial.Serial(AUX_MEGA_PORT, baudrate=9600, timeout=1)
    except Exception as exc:
        _diag(f"Aux Mega port {AUX_MEGA_PORT} unavailable ({exc!s}). Running in simulation mode.")
        return None


def main() -> None:
    aux = _open_aux()

    readers = {
        "auxmega": open_reader(CONTROL_FILES["auxmega"]),
        "jaw": open_reader(CONTROL_FILES["jaw"]),
        "eye": open_reader(CONTROL_FILES["eye"]),
        "gardan": open_reader(CONTROL_FILES["gardan"]),
        "rolls": open_reader(CONTROL_FILES["rolls"]),
    }

    append_message(STATUS_FILES["auxmega"], "1")

    try:
        while True:
            should_stop = False
            dispatched = False

            for channel, reader in readers.items():
                command = read_available(reader)
                if not command:
                    continue

                if command == "-1":
                    should_stop = True
                    break

                if channel == "auxmega":
                    continue

                payload = f"{PREFIX_BY_CHANNEL[channel]}:{command}\n"
                dispatched = True

                if aux is not None:
                    try:
                        aux.write(payload.encode("utf-8"))
                    except Exception as exc:
                        _diag(f"Shared aux Mega connection lost ({exc!s}); continuing in simulation mode.")
                        try:
                            aux.close()
                        except Exception:
                            pass
                        aux = None

            if should_stop:
                break

            if not dispatched:
                time.sleep(0.05)
    finally:
        append_message(STATUS_FILES["auxmega"], "2")
        if aux is not None:
            try:
                aux.close()
            except Exception:
                pass
        for reader in readers.values():
            try:
                reader.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
