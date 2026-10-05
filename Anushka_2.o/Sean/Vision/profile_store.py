from __future__ import annotations

import json
from pathlib import Path


PROFILE_FILE = Path(__file__).resolve().parent / "person_profiles.json"

DEFAULT_GESTURE = "12"
UNKNOWN_GESTURE = "6"


def pretty_name(name: str) -> str:
    return str(name).replace("_", " ").strip()


def normalize_token(value: str) -> str:
    return pretty_name(value).lower()


def _load_profiles() -> dict[str, dict]:
    try:
        with PROFILE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_profiles(profiles: dict[str, dict]) -> None:
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PROFILE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(profiles, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def ensure_profile(raw_name: str) -> dict:
    profiles = _load_profiles()
    if raw_name in profiles:
        return profiles[raw_name]

    profile = {
        "display_name": pretty_name(raw_name),
        "greeting": f"Jaye heend {pretty_name(raw_name)}",
        "gesture": DEFAULT_GESTURE,
        "aliases": [normalize_token(raw_name)],
    }
    profiles[raw_name] = profile
    save_profiles(profiles)
    return profile


def resolve_profile(raw_name: str) -> dict:
    profiles = _load_profiles()
    if raw_name in profiles:
        return profiles[raw_name]

    target = normalize_token(raw_name)
    for key, profile in profiles.items():
        aliases = profile.get("aliases", [])
        if any(normalize_token(alias) == target for alias in aliases):
            return profile
        if target and target in normalize_token(key):
            return profile

    return {
        "display_name": pretty_name(raw_name),
        "greeting": f"Jaye heend {pretty_name(raw_name)}",
        "gesture": DEFAULT_GESTURE,
        "aliases": [target] if target else [],
    }


def canonical_display_name(raw_name: str) -> str:
    profile = resolve_profile(raw_name)
    return profile.get("display_name", pretty_name(raw_name))


def greeting_for_name(raw_name: str) -> str:
    profile = resolve_profile(raw_name)
    return profile.get("greeting", f"Jaye heend {canonical_display_name(raw_name)}")


def gesture_for_name(raw_name: str, default: str = DEFAULT_GESTURE) -> str:
    profile = resolve_profile(raw_name)
    return str(profile.get("gesture", default))
