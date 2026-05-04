from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from Brain.AIBrain import replyBrain
from Speech.essentialFunctions import set2Female, set2Male, speakAndGest


def replyBrainForCharacter(question: str, character: str = "2") -> str:
    # Kept for older imports; the modern brain uses one multilingual Anooshka persona.
    return replyBrain(question)


if __name__ == "__main__":
    print("Modern brain/speech console. Type 'exit' to stop.")
    character = input("1. Male\n2. Female\n3. Champa\n4. Vinaayak\n").strip()
    if character in {"1", "4"}:
        set2Male()
    else:
        set2Female()

    while True:
        query = input("Enter: ").strip()
        if query.lower() in {"exit", "quit", "-1"}:
            break
        if not query:
            continue
        reply = replyBrainForCharacter(query, character)
        print(reply)
        speakAndGest(reply)
