from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from anushka_runtime.config import LOG_FILES
from anushka_runtime.openai_bridge import OpenAIRobotBridge, OpenAIUnavailableError


bridge = OpenAIRobotBridge()
last5Queries: list[tuple[str, str]] = []


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""


def _history_lines() -> list[str]:
    return [f"You: {question}\nAnooshka: {answer}" for question, answer in last5Queries[-5:]]


def replyBrain(question: str) -> str:
    knowledge = _read_text(LOG_FILES["knowledge"])
    persona = _read_text(LOG_FILES["persona"])
    history = [persona, *_history_lines()]

    try:
        answer = bridge.respond(
            user_query=question,
            conversation_history=history,
            knowledge=knowledge,
            currently_present="",
        )
    except OpenAIUnavailableError:
        return "OpenAI is not configured yet. Please set OPENAI_API_KEY in the .env file."
    except Exception as exc:
        return f"I could not reach the AI service right now: {exc}"

    if answer:
        last5Queries.append((question, answer))
        del last5Queries[:-5]
    return answer


if __name__ == "__main__":
    print("Anooshka brain console. Type 'exit' to stop.")
    while True:
        query = input("Enter: ").strip()
        if query.lower() in {"exit", "quit", "-1"}:
            break
        if not query:
            continue
        print(replyBrain(query))
