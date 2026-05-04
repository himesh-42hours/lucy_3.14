from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from anushka_runtime.config import LOG_FILES


def add2Knowledge(question: str, answer: str) -> None:
    LOG_FILES["knowledge"].parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILES["knowledge"].open("a", encoding="utf-8") as file_obj:
        file_obj.write(f"Q: {question}\nA: {answer}\n")


if __name__ == "__main__":
    while True:
        q = input("Q: ").strip()
        if q.lower() in {"exit", "quit", "-1"}:
            break
        a = input("A: ").strip()
        add2Knowledge(q, a)
        print("Learnt.")
