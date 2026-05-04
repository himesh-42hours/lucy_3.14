from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from anushka_runtime.config import CHAT_MODEL
from anushka_runtime.openai_bridge import OpenAIRobotBridge, OpenAIUnavailableError


BAAT_CHEET_PATH = Path(__file__).resolve().with_name("conversation_cache.txt")
ALLOWED_EFFECTS = {"chuckle", "yawn", "whistle", "hum", "none"}


def select_sound_effect(text: str) -> str:
    if not text.strip():
        return "none"

    bridge = OpenAIRobotBridge()
    try:
        client = bridge._require_client()
        response = client.responses.create(
            model=CHAT_MODEL,
            temperature=0.2,
            max_output_tokens=20,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Choose exactly one sound effect for the robot after this reply: "
                                "chuckle, yawn, whistle, hum, or none. Return only that word."
                            ),
                        }
                    ],
                },
                {"role": "user", "content": [{"type": "input_text", "text": text}]},
            ],
        )
    except OpenAIUnavailableError:
        return "none"

    effect = (response.output_text or "none").strip().lower()
    return effect if effect in ALLOWED_EFFECTS else "none"


def main() -> None:
    text = BAAT_CHEET_PATH.read_text(encoding="utf-8", errors="ignore") if BAAT_CHEET_PATH.exists() else ""
    BAAT_CHEET_PATH.write_text(select_sound_effect(text), encoding="utf-8")


if __name__ == "__main__":
    main()
