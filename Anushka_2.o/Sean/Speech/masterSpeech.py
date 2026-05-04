from __future__ import annotations

from pathlib import Path
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from anushka_runtime.config import CONTROL_FILES, STATUS_FILES
from anushka_runtime.ipc import ensure_file, open_reader, read_available, write_text
from Speech.essentialFunctions import greet, set2Female, set2Male, speakAndGest


def handle_command(command: str) -> bool:
    if command == "-1":
        return False
    if command == "-2":
        return False
    if command == "0":
        set2Male()
    elif command == "1":
        set2Female()
    elif command == "2":
        greet()
    return True


def main() -> None:
    ensure_file(CONTROL_FILES["speech"])
    ensure_file(CONTROL_FILES["speech_command"])
    write_text(STATUS_FILES["speech"], "1\n")

    speech_reader = open_reader(CONTROL_FILES["speech"])
    command_reader = open_reader(CONTROL_FILES["speech_command"])
    try:
        speakAndGest("Speech module is now active.")
        while True:
            command = read_available(command_reader)
            if command and not handle_command(command):
                break

            sentence = read_available(speech_reader)
            if sentence == "-1":
                break
            if sentence:
                speakAndGest(sentence)

            time.sleep(0.1)
    finally:
        speech_reader.close()
        command_reader.close()


if __name__ == "__main__":
    main()
