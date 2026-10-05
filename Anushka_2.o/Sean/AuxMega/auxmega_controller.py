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


EYE_COMMANDS = {
    "0": "EYES:CENTER",
    "1": "EYES:CENTER",
    "2": "EYES:CENTER",
    "3": "EYES:CENTER",
    "4": "EYES:UP",
    "5": "EYES:DOWN",
    "6": "BLINK",
    "7": "BLINK",
    "8": "BLINK",
    "9": "BLINK",
    "10": "BLINK",
    "11": "BLINK",
    "12": "BLINK",
    "13": "BLINK",
    "14": "BLINK",
    "15": "BLINK",
    "-2": "EYES:CENTER",
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
        _diag("ANUSHKA_HEAD_MEGA_PORT / ANUSHKA_AUX_MEGA_PORT is not set. Running in simulation mode.")
        return None
    try:
        return serial.Serial(AUX_MEGA_PORT, baudrate=9600, timeout=1)
    except Exception as exc:
        _diag(f"Head Mega port {AUX_MEGA_PORT} unavailable ({exc!s}). Running in simulation mode.")
        return None


def main() -> None:
    aux = _open_aux()

    talk_active = False
    talk_end_at = 0.0

    def send_line(payload: str) -> None:
        nonlocal aux
        if aux is None:
            return
        try:
            aux.write(f"{payload}\n".encode("utf-8"))
        except Exception as exc:
            _diag(f"Shared aux Mega connection lost ({exc!s}); continuing in simulation mode.")
            try:
                aux.close()
            except Exception:
                pass
            aux = None

    def _parse_seconds(value: str) -> float | None:
        try:
            return float(value)
        except ValueError:
            return None

    def start_talk(seconds: float | None) -> None:
        nonlocal talk_active, talk_end_at
        if not talk_active:
            send_line("TALK:1")
        talk_active = True
        if seconds is not None:
            talk_end_at = max(talk_end_at, time.time() + seconds)

    def stop_talk() -> None:
        nonlocal talk_active, talk_end_at
        if talk_active:
            send_line("TALK:0")
        talk_active = False
        talk_end_at = 0.0

    def handle_jaw(command: str) -> None:
        nonlocal talk_active, talk_end_at
        cmd = command.strip()
        if not cmd:
            return

        upper = cmd.upper()
        if upper in {"OPEN", "CLOSE"}:
            stop_talk()
            send_line(f"JAW:{upper}")
            return

        if upper.startswith("TALK:"):
            if upper.endswith("0"):
                stop_talk()
            else:
                send_line("TALK:1")
                talk_active = True
                talk_end_at = 0.0
            return

        if upper.startswith("JAW:"):
            stop_talk()
            send_line(upper)
            return

        seconds = _parse_seconds(cmd)
        if seconds is None:
            return
        if seconds <= 0:
            stop_talk()
            return
        start_talk(seconds)

    def handle_eye(command: str) -> None:
        cmd = command.strip()
        if not cmd:
            return

        upper = cmd.upper()
        if upper.startswith("EYES:") or upper == "BLINK":
            send_line(upper)
            return

        mapped = EYE_COMMANDS.get(cmd)
        if mapped:
            send_line(mapped)
            return

        send_line("BLINK")

    def handle_gardan(command: str) -> None:
        cmd = command.strip()
        if not cmd:
            return

        upper = cmd.upper()
        if upper.startswith("NOD:") or upper.startswith("NECK:"):
            send_line(upper)
            return

        if upper in {"YES", "NO"}:
            send_line(f"NOD:{upper}")
            return

        if cmd == "-2":
            send_line("NECK:90")
            return

        angle = _parse_seconds(cmd)
        if angle is None:
            return
        send_line(f"NECK:{int(angle)}")

    readers = {
        "auxmega": open_reader(CONTROL_FILES["auxmega"]),
        "jaw": open_reader(CONTROL_FILES["jaw"]),
        "eye": open_reader(CONTROL_FILES["eye"]),
        "gardan": open_reader(CONTROL_FILES["gardan"]),
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
                    send_line(command)
                    dispatched = True
                    continue

                if channel == "jaw":
                    handle_jaw(command)
                    dispatched = True
                elif channel == "eye":
                    handle_eye(command)
                    dispatched = True
                elif channel == "gardan":
                    handle_gardan(command)
                    dispatched = True

            if should_stop:
                break

            if talk_active and talk_end_at > 0 and time.time() >= talk_end_at:
                stop_talk()

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
