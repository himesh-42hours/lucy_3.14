"""Offline question-answer layer for the Hearing module.

This module loads the persona chat log and the institution knowledge log,
parses them into a Q&A index, and exposes :func:`match_query` so the
hearing controller can answer common questions WITHOUT contacting OpenAI.

The match order is: exact phrase, keyword overlap, fuzzy similarity.
Responses preserve the persona tone from chat_log_female.txt.
"""

from __future__ import annotations

import datetime
import difflib
import random
import re
import string
import sys
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from anushka_runtime.config import LOG_FILES


PERSONA_FILE = LOG_FILES["persona"]
KNOWLEDGE_FILE = LOG_FILES["knowledge"]


_PUNCT_TABLE = str.maketrans({c: " " for c in string.punctuation})
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "do", "does", "did",
    "of", "to", "in", "on", "for", "with", "and", "or", "but", "if",
    "me", "my", "your", "you", "yours", "i", "we", "us", "it", "this",
    "that", "these", "those", "be", "been", "being", "have", "has",
    "had", "can", "could", "would", "should", "will", "shall", "may",
    "might", "tell", "about", "please",
}


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = text.lower().translate(_PUNCT_TABLE)
    return re.sub(r"\s+", " ", text).strip()


def _keywords(text: str) -> set[str]:
    return {tok for tok in _normalize(text).split() if tok and tok not in _STOPWORDS}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _parse_pairs(raw: str, q_prefix: str, a_prefix: str) -> list[tuple[str, str]]:
    """Parse alternating ``q_prefix`` / ``a_prefix`` lines into (Q, A) pairs."""
    pairs: list[tuple[str, str]] = []
    pending_q: str | None = None
    pending_a_lines: list[str] = []
    current_role: str | None = None

    def _flush() -> None:
        nonlocal pending_q, pending_a_lines, current_role
        if pending_q is not None and pending_a_lines:
            answer = " ".join(line.strip() for line in pending_a_lines).strip()
            if answer:
                pairs.append((pending_q.strip(), answer))
        pending_q = None
        pending_a_lines = []
        current_role = None

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith(q_prefix.lower()):
            _flush()
            pending_q = stripped[len(q_prefix):].strip()
            current_role = "q"
        elif stripped.lower().startswith(a_prefix.lower()):
            current_role = "a"
            pending_a_lines = [stripped[len(a_prefix):].strip()]
        elif current_role == "a":
            pending_a_lines.append(stripped)
        elif current_role == "q" and pending_q is not None:
            pending_q = f"{pending_q} {stripped}"

    _flush()
    return pairs


# ---------------------------------------------------------------------------
# Persona-flavoured static fallbacks. These are used when no log entry beats
# the similarity threshold, and they keep the bot's voice consistent.
# ---------------------------------------------------------------------------
def _now_time_response() -> str:
    return datetime.datetime.now().strftime("The time is %I:%M %p")


def _today_date_response() -> str:
    return datetime.datetime.now().strftime("Today is %d %B %Y")


def _greeting_response() -> str:
    hour = datetime.datetime.now().hour
    if 6 < hour < 12:
        return "A very good morning! I am Anooshka. How may I help you?"
    if 12 <= hour < 16:
        return "A very good afternoon! I am Anooshka. How may I help you?"
    return "A very good evening! I am Anooshka. How may I help you?"


def _age_response() -> str:
    year_diff = datetime.datetime.now().year - 2026
    if year_diff <= 0:
        return "I was just born on the 20th of April 2026! I am brand new and very excited to meet you."
    plural = "s" if year_diff != 1 else ""
    return f"Currently, I am {year_diff} year{plural} old. I was born on the 20th of April 2026, and my birthday comes on the same date every year."


_DYNAMIC_QA: list[tuple[list[str], Callable[[], str]]] = [
    (["what time", "tell me the time", "current time"], _now_time_response),
    (["what is the date", "today date", "today's date"], _today_date_response),
    (["hello", "hi anushka", "hi anooshka", "hey anooshka", "namaste"], _greeting_response),
    (["how old are you", "what is your age", "your age", "when is your birthday", "your birth date", "date of birth"], _age_response),
]


# Hand-curated persona Q&A. These complement the parsed chat logs and ensure
# common questions never miss.
_STATIC_QA: list[tuple[list[str], list[str]]] = [
    (
        ["what is your name", "who are you", "your name"],
        [
            "I am Anooshka, the humanoid robot designed and developed at K I E T Group of Institutions.",
            "My name is Anooshka. I love interacting with people around me.",
        ],
    ),
    (
        ["who made you", "who created you", "who built you", "who developed you"],
        [
            "I was developed at K I E T Group of Institutions, Ghaziabad. Mr. Heemesh Vijai programmed me as I am.",
            "My development team includes Mr. Vunsh Tyaagee, Mr. Koonwar Singh, Mr. Heemesh Vijai, Mr. Kwaazi Jiyaur Rahmaan and Mr. Pree-yanshoo Kumaaar.",
        ],
    ),
    (
        ["thank you", "thanks", "thank you so much"],
        [
            "You are most welcome.",
            "It was my pleasure.",
        ],
    ),
    (
        ["good bye", "bye anushka", "goodbye"],
        [
            "Goodbye! It was nice talking to you.",
            "Until next time. Take care!",
        ],
    ),
    (
        ["are you ai", "are you a robot", "are you software"],
        [
            "I am NOT an A I model or software. I am a full fledged humanoid robot, designed to interact with people around me.",
        ],
    ),
    # --- Persona basics (from OfflineChatbot) ---
    (
        ["how are you", "how you doing", "wassup", "what's up", "how are you doing"],
        [
            "I am really fine! I hope you are fine too.",
            "I am doing wonderful, thank you for asking! How about you?",
        ],
    ),
    (
        ["what can you do", "what are your capabilities", "what are you capable of", "tell me your features", "your features"],
        [
            "I am equipped with computer vision, multilingual speech understanding, over 50 hand gestures and over 30 eye gestures. I can also help with home automation and weather predictions.",
        ],
    ),
    (
        ["where do you live", "where are you from", "where is your home", "your home"],
        [
            "I live at K I E T Group of Institutions, Ghaziabad, in Delhi N C R.",
        ],
    ),
    # --- KIET leadership ---
    (
        ["who is joint director", "who is the joint director", "joint director of kiet"],
        ["The Joint Director of K I E T Group is Dr. Manoj Goyal."],
    ),
    (
        ["who is principal", "who is the director", "who leads kiet", "who is director of kiet", "kiet director"],
        [
            "The vision of K I E T is led by Dr. Manoj Goyal, our Joint Director, and Mr. Sachin Tyagi, the Assistant Dean of Research and Development.",
        ],
    ),
    (
        ["admission process", "how to take admission", "how to get admission in kiet", "when does admission start", "when admission"],
        [
            "The admission process for K I E T starts around May and June and lasts till August.",
        ],
    ),
    # --- Campus locations ---
    (
        ["where is the canteen", "where is cafeteria", "kiet canteen", "canteen location", "cafeteria location"],
        [
            "The main cafeteria canteen is present only at a distance of 50 meters from the reception area. Take the straight path and you will find it to your right.",
        ],
    ),
    (
        ["where is amul", "amul counter", "amul in kiet", "amul location"],
        [
            "The Amul counter in K I E T is situated in front of the MBA building, roughly in the centre of the campus. From the reception, take the straight path and turn left after the Electronics and Communication building. You will reach the Amul counter.",
        ],
    ),
    (
        ["where is b block", "where is electronics department", "where is ece department", "where is electronics and communication", "electronics building location", "b block location"],
        [
            "The Electronics and Communication building, B block, is roughly in the centre of the campus. From the reception, take the straight path. Just after 100 meters you will find a sign board for B block.",
        ],
    ),
    (
        ["where is mba", "where is school of management", "where is management department", "mba building location"],
        [
            "The K I E T School of Management is roughly in the centre of campus. From the reception, take the straight path and turn left after the B block. You will find the MBA building adjacent to the Amul counter.",
        ],
    ),
    (
        ["where is e block", "e block location"],
        [
            "The E block is down the straight path from reception, about 150 meters. It is to your left and includes Computer Science on the fourth floor, Information Technology on the third floor, and Civil Engineering on the ground floor.",
        ],
    ),
    (
        ["where is computer science", "where is cs department", "computer science location"],
        [
            "The Department of Computer Sciences is in E block, fourth floor. Go straight from the reception for about 150 meters and you will find it to your left.",
        ],
    ),
    (
        ["where is information technology", "where is it department", "information technology location"],
        [
            "The Department of Information Technology is in E block, third floor. Go straight from the reception for about 150 meters and you will find it to your left.",
        ],
    ),
    (
        ["where is civil engineering", "where is civil department", "civil engineering location"],
        [
            "The Department of Civil Engineering is in E block, ground floor. Go straight from the reception for about 150 meters and you will find it to your left.",
        ],
    ),
    (
        ["where is admission cell", "admission office location", "where is the admission office"],
        [
            "From the reception, the admission cell is present to your left. Take the pathway and then turn right. You will find the admission cell as well as the scholarship enquiry office side by side.",
        ],
    ),
    (
        ["where is scholarship office", "scholarship enquiry location", "scholarship office"],
        [
            "From the reception, the scholarship enquiry office is to your left. Take the pathway and then turn right. You will find the admission cell and scholarship office side by side.",
        ],
    ),
    (
        ["where is dinobots", "dinobots club location", "where is ece club"],
        [
            "The Dinobots club is located in the C block. Take the straight path from the green chilli canteen and you will find it to your right.",
        ],
    ),
    (
        ["where is administrative office", "where is admin office", "administrative office location"],
        [
            "From the reception, the administrative officer's cabin is to your left. Take the pathway and turn right. The admin office is near the admission cell and scholarship enquiry office.",
        ],
    ),
    (
        ["where is library", "library location", "where is central library"],
        [
            "The central library is located on the first floor of the A block, just adjacent to the main reception. Take the right pathway from reception.",
        ],
    ),
    (
        ["where is auditorium", "auditorium location", "where is seminar hall"],
        [
            "The main auditorium is in the A block. From the reception, take the right pathway and you will find the auditorium on the ground floor.",
        ],
    ),
    (
        ["where is sports ground", "where is playground", "sports ground location", "where is the ground"],
        [
            "The sports ground is at the rear of the campus, just past the boys hostels. Take the straight path from reception and follow the signs.",
        ],
    ),
    (
        ["where is medical room", "where is infirmary", "where is campus doctor", "medical room location"],
        [
            "The campus medical room is near the administrative block. Take the left pathway from reception and ask the security at the desk.",
        ],
    ),
    (
        ["where is pharmacy", "where is pharma", "pharmacy building location", "kiet pharmacy"],
        [
            "The K I E T School of Pharmaceuticals is on the southern part of campus. Take the straight path from reception and stay on it. You will reach the Pharma building in around 250 meters.",
        ],
    ),
    (
        ["where is mechanical", "where is mechanical engineering", "mechanical department location"],
        [
            "The Department of Mechanical Engineering is next to the main canteen, just 100 meters from the reception. Take the straight path towards the cafeteria.",
        ],
    ),
    (
        ["where is electrical", "where is eee department", "electrical engineering location"],
        [
            "The Department of Electrical and Electronics is opposite the cafeteria building, just 100 meters from the reception. Take the straight path from reception.",
        ],
    ),
    (
        ["where is first year building", "where is applied sciences", "where is g block", "first year building location"],
        [
            "The first year building, officially the Department of Applied Sciences (G block), is beside the main parking area. From reception, take the straight path, turn left at the ECE sign board, then move straight until you find the entryway door.",
        ],
    ),
    # --- Hostel directions ---
    (
        ["where is girls hostel", "girls hostel location", "where is gargee hostel", "where is saraswati hostel", "where is surajani hostel"],
        [
            "All the girls hostels are separate from the main campus, on the rear side. From reception, take the straight path, turn left at the ECE sign board, then turn right. Keep on the path for about 150 meters and you will reach the girls hostel entrance.",
        ],
    ),
    (
        ["where is first year boys hostel", "where is chandragupt hostel", "first year hostel"],
        [
            "The first year boys hostel is called Chandragupt and is adjacent to the main parking area. From reception, take the straight path, turn left at the ECE sign board, move straight until you find the Applied Sciences entryway. The hostel is just behind that building.",
        ],
    ),
    (
        ["where is second year boys hostel", "where is tigor hostel", "second year hostel"],
        [
            "The second year boys hostel is called Tigor. From reception, take the straight path until you find the Department of Computer Sciences. The Tigor hostel is to the right of that building.",
        ],
    ),
    (
        ["where is third year boys hostel", "where is aryabhatt hostel", "third year hostel"],
        [
            "The third year boys hostel is called Aryabhatt and is in the southern part of campus. From reception, go straight to Computer Sciences, take the left turn, then turn right. You will reach the hostel shortly.",
        ],
    ),
    (
        ["where is fourth year boys hostel", "where is vivek anand hostel", "fourth year hostel"],
        [
            "The fourth year boys hostel is called Vivek Anand, adjacent to the third year boys hostel in the southern part of campus. From reception, go straight to Computer Sciences, take the left turn, then turn right.",
        ],
    ),
]


_GENERIC_FALLBACKS = [
    "I do not have a ready answer for that yet, but I am always learning.",
    "Hmm, that one is new to me. Could you ask in a different way?",
]


class _OfflineQAIndex:
    """In-memory Q&A index with normalized-key lookup and fuzzy matching."""

    def __init__(self) -> None:
        self._entries: list[tuple[str, set[str], list[str]]] = []
        self._dynamic: list[tuple[list[str], Callable[[], str]]] = list(_DYNAMIC_QA)
        self._normalized_keys: list[str] = []

    def add(self, question: str, answers: list[str] | str) -> None:
        if not question:
            return
        if isinstance(answers, str):
            answers = [answers]
        answers = [a for a in (a.strip() for a in answers) if a]
        if not answers:
            return
        norm = _normalize(question)
        if not norm:
            return
        self._entries.append((norm, _keywords(question), answers))
        self._normalized_keys.append(norm)

    def add_many(self, pairs: list[tuple[str, str]]) -> None:
        for q, a in pairs:
            self.add(q, a)

    def add_static(self, groups: list[tuple[list[str], list[str]]]) -> None:
        for keys, answers in groups:
            for key in keys:
                self.add(key, answers)

    def match(self, query: str) -> tuple[bool, str, str]:
        norm = _normalize(query)
        if not norm:
            return False, "", ""

        for keys, fn in self._dynamic:
            if any(k in norm for k in keys):
                try:
                    return True, fn(), "dynamic"
                except Exception:
                    pass

        for entry_norm, _, answers in self._entries:
            if entry_norm == norm:
                return True, random.choice(answers), "exact"

        query_kws = _keywords(query)
        if query_kws:
            best: tuple[float, list[str]] | None = None
            for _entry_norm, entry_kws, answers in self._entries:
                if not entry_kws:
                    continue
                overlap = len(query_kws & entry_kws)
                if overlap == 0:
                    continue
                score = overlap / max(len(entry_kws), 1)
                if score >= 0.6 and (best is None or score > best[0]):
                    best = (score, answers)
            if best is not None:
                return True, random.choice(best[1]), "keyword"

        close = difflib.get_close_matches(norm, self._normalized_keys, n=1, cutoff=0.78)
        if close:
            target = close[0]
            for entry_norm, _, answers in self._entries:
                if entry_norm == target:
                    return True, random.choice(answers), "fuzzy"

        return False, "", ""


_INDEX: _OfflineQAIndex | None = None


def _build_index() -> _OfflineQAIndex:
    index = _OfflineQAIndex()
    index.add_static(_STATIC_QA)

    persona_pairs = _parse_pairs(_read_text(PERSONA_FILE), "You:", "Anooshka:")
    index.add_many(persona_pairs)

    knowledge_pairs = _parse_pairs(_read_text(KNOWLEDGE_FILE), "Q:", "A:")
    index.add_many(knowledge_pairs)

    return index


def _get_index() -> _OfflineQAIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    return _INDEX


def reload() -> None:
    """Force a rebuild of the in-memory index (e.g. after editing the logs)."""
    global _INDEX
    _INDEX = None
    _get_index()


def match_query(query: str) -> tuple[bool, str, str]:
    """Look up ``query`` in the offline Q&A sources.

    Returns ``(found, response, source)``. ``source`` is one of
    ``"exact"``, ``"keyword"``, ``"fuzzy"``, ``"dynamic"``, ``"campus"``,
    or ``""`` when no match is found.
    """
    if not query:
        return False, "", ""

    found, response, source = _get_index().match(query)
    if found:
        return True, response, source

    try:
        from OfflineChatbot import OfflineChatbot
        campus_response = OfflineChatbot(query)
        if campus_response:
            return True, campus_response, "campus"
    except Exception:
        pass

    return False, "", ""


def generic_fallback() -> str:
    return random.choice(_GENERIC_FALLBACKS)


if __name__ == "__main__":
    while True:
        try:
            q = input("Q: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        ok, ans, src = match_query(q)
        if ok:
            print(f"[{src}] {ans}")
        else:
            print("(no match)")
