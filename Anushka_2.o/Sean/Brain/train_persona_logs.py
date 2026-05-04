from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from anushka_runtime.config import path_for


PERSONA_FILES = {
    "1": ("Vinaayak", path_for("Sean", "Brain", "Database", "chat_log_male.txt")),
    "2": ("Anooshka", path_for("Sean", "Brain", "Database", "chat_log_female.txt")),
    "3": ("Champa", path_for("Sean", "Brain", "Database", "chat_log_champa.txt")),
    "4": ("Vinaayak", path_for("Sean", "Brain", "Database", "chat_log_vinaayak.txt")),
}


def addToPersona(question: str, answer: str, character: str) -> None:
    name, path = PERSONA_FILES.get(character, PERSONA_FILES["2"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(f"\nYou: {question}\n{name}: {answer}\n")
    print("Learnt.")


if __name__ == "__main__":
    print("Persona definition training")
    chara = input("1. Male\n2. Female\n3. Champa\n4. Vinaayak\n").strip()
    while True:
        question = input("Enter user question: ").strip()
        if question.lower() in {"exit", "quit", "-1"}:
            break
        answer = input("Enter AI answer: ").strip()
        addToPersona(question, answer, chara)
