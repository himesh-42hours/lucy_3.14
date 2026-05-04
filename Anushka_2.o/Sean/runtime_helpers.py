from __future__ import annotations

import random
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SEAN_ROOT = REPO_ROOT / "Sean"
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from anushka_runtime.config import CONTROL_FILES, LOG_FILES
from anushka_runtime.ipc import append_message


alreadySaid = [
    "As I have already said",
    "As I have already told",
    "I just told it a moment back",
    "I think I told it a while back",
    "I think I am having a deja vu, but I told it just a moment ago",
    "Haven't I told it already?",
    "Okay, I will repeat myself",
]
YesList = ["yes", "yes please", "ok", "okay", "haan", "yup", "zaroor", "bilkul"]
NoList = ["bilkul nahi", "no", "nope", "nahi", "ille", "naako", "leave it"]
Assnames = ["jarvis", "friday", "edith", "strange", "bismillah", "chitti", "lucy"]
Sassnames = ["wednesday", "M.J", "penny", "soul"]
Massnames = ["sir", "master", "master ji", "king almighty", "sire", "my lord", "jahapana"]


def retOutOf(items: list[str]) -> str:
    return random.choice(items)


def writeToJaw(gesture: str) -> None:
    append_message(CONTROL_FILES["jaw"], gesture)


def writeToTestLog(text: str) -> None:
    append_message(LOG_FILES["test"], text)


def pauseHearing() -> None:
    append_message(CONTROL_FILES["hear"], "0")


def playHearing() -> None:
    append_message(CONTROL_FILES["hear"], "1")


def writeToHaath(gesture: str) -> None:
    append_message(CONTROL_FILES["haath"], gesture)


def writeToRolls(gesture: str) -> None:
    append_message(CONTROL_FILES["rolls"], gesture)


def writeToEye(gesture: str) -> None:
    append_message(CONTROL_FILES["eye"], gesture)


def AllCheck(items: list[str], query: str) -> bool:
    return all(item in query for item in items)


def ListCheck(items: list[str], query: str) -> str:
    for item in items:
        if item in query:
            return item
    return ""


def selectOutOf(items: list[str]) -> str:
    return random.choice(items)
