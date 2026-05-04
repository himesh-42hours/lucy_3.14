from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Iterable, Optional

from openai import OpenAI

from .config import (
    CHAT_MODEL,
    ENABLE_LANGUAGE_MIRROR,
    OPENAI_API_KEY,
    OPENAI_TRANSCRIBE_LANGUAGE,
    REPLY_LANGUAGE,
    TRANSCRIBE_MODEL,
    TTS_INSTRUCTIONS,
    TTS_MODEL,
    TTS_SPEED,
    TTS_VOICE,
)


class OpenAIUnavailableError(RuntimeError):
    pass


class OpenAIRobotBridge:
    def __init__(self, api_key: str = OPENAI_API_KEY) -> None:
        self._client = OpenAI(api_key=api_key) if api_key else None

    @property
    def available(self) -> bool:
        return self._client is not None

    def _require_client(self) -> OpenAI:
        if self._client is None:
            raise OpenAIUnavailableError("OPENAI_API_KEY is not configured.")
        return self._client

    def normalize_to_english(self, query: str) -> str:
        if not query.strip():
            return query
        client = self._require_client()
        response = client.responses.create(
            model=CHAT_MODEL,
            temperature=0.1,
            max_output_tokens=120,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Translate the user's message into concise, natural English for internal command handling. "
                                "Preserve names, proper nouns, and intent. Return only the translated sentence."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": query}],
                },
            ],
        )
        return (response.output_text or query).strip()

    def respond(
        self,
        *,
        user_query: str,
        conversation_history: Iterable[str],
        knowledge: str,
        currently_present: str,
    ) -> str:
        """Generate a chat response using Chat Completions.

        Knowledge and persona go in the SYSTEM message (prompt-cached on
        repeated calls). Conversation history is sent as proper alternating
        user/assistant turns — no text is duplicated per call.
        """
        client = self._require_client()

        # Build system prompt once; OpenAI caches this prefix automatically
        # when the same content recurs across calls.
        language_instruction = "Reply in the same language and script as the user's latest message unless they ask otherwise."
        if REPLY_LANGUAGE != "auto":
            if REPLY_LANGUAGE in {"en", "english"}:
                language_instruction = "Reply in English (India) unless the user explicitly asks for another language."
            elif REPLY_LANGUAGE in {"hi", "hindi"}:
                language_instruction = "Reply in Hindi (Devanagari script) unless the user explicitly asks for another language."
            elif REPLY_LANGUAGE in {"hinglish"}:
                language_instruction = "Reply in Hinglish (Hindi written in Latin script) unless the user explicitly asks for another language."
            else:
                language_instruction = f"Reply in {REPLY_LANGUAGE} unless the user explicitly asks for another language."

        system_parts = [
            "You are Anooshka, a warm humanoid robot speaking aloud to visitors at K I E T Group of Institutions.",
            language_instruction,
            "Keep answers natural for speech, concise, and grounded in the knowledge base below.",
            "If you do not know something, admit that honestly.",
            "Do not mention prompts, tokens, policies, or internal files.",
        ]
        if knowledge.strip():
            system_parts.append(f"\nKnowledge base:\n{knowledge.strip()}")
        system_text = "\n".join(system_parts)

        # Build message list: system + prior turns + current query.
        messages: list[dict] = [{"role": "system", "content": system_text}]

        for line in conversation_history:
            if line.startswith("User: "):
                messages.append({"role": "user", "content": line[6:]})
            elif line.startswith("Anooshka: "):
                messages.append({"role": "assistant", "content": line[10:]})

        # Append context that changes per turn (who is present) + the query.
        context_prefix = (
            f"[Visible: {currently_present}] " if currently_present and currently_present.lower() not in {"", "none", "unknown"} else ""
        )
        messages.append({"role": "user", "content": f"{context_prefix}{user_query}"})

        response = client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0.5,
            max_tokens=260,
            messages=messages,
        )
        return (response.choices[0].message.content or "").strip()

    def mirror_language(self, user_query: str, english_reply: str) -> str:
        if REPLY_LANGUAGE != "auto" or not ENABLE_LANGUAGE_MIRROR:
            return english_reply
        client = self._require_client()
        response = client.responses.create(
            model=CHAT_MODEL,
            temperature=0.2,
            max_output_tokens=180,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Rewrite the assistant reply in the same language and script as the user's message. "
                                "If the user explicitly requested another language, obey that request. "
                                "Keep the meaning intact and return only the final reply."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"User message: {user_query}\nAssistant reply to rewrite: {english_reply}",
                        }
                    ],
                },
            ],
        )
        return (response.output_text or english_reply).strip()

    def transcribe_wav(self, wav_bytes: bytes) -> str:
        client = self._require_client()
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_audio:
            temp_audio.write(wav_bytes)
            temp_audio.flush()
            with open(temp_audio.name, "rb") as file_obj:
                kwargs = {"model": TRANSCRIBE_MODEL, "file": file_obj}
                # If OPENAI_TRANSCRIBE_LANGUAGE is empty, let the service auto-detect.
                if OPENAI_TRANSCRIBE_LANGUAGE and OPENAI_TRANSCRIBE_LANGUAGE.lower() != "auto":
                    kwargs["language"] = OPENAI_TRANSCRIBE_LANGUAGE
                transcript = client.audio.transcriptions.create(**kwargs)
        return transcript.text.strip()

    def speech_to_file(self, text: str, output_path: Path) -> None:
        client = self._require_client()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        kwargs = {
            "model": TTS_MODEL,
            "voice": TTS_VOICE,
            "input": text,
            "speed": TTS_SPEED,
        }
        if TTS_INSTRUCTIONS:
            kwargs["instructions"] = TTS_INSTRUCTIONS

        # The SDK has exposed both streaming and file-write helpers across versions.
        try:
            with client.audio.speech.with_streaming_response.create(**kwargs) as response:
                response.stream_to_file(output_path)
            return
        except Exception:
            pass

        response = client.audio.speech.create(**kwargs)
        if hasattr(response, "write_to_file"):
            response.write_to_file(output_path)
        else:
            output_path.write_bytes(response.read())
