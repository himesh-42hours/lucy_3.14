"""Persistent face-encoding cache for the Vision module.

Stores (names, encodings, image-mtimes) in ``face_cache.pkl`` next to the
faces directory and returns cached data when the on-disk images have not
changed — eliminating the expensive per-startup re-encoding step.

Usage::

    cache = FaceCache(FACES_DIR, CACHE_PATH)
    result = cache.load()
    if result is None:                     # images changed → rebuild
        encodings, names = _build(...)
        cache.save(encodings, names)
    else:
        encodings, names = result          # instant startup
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_VERSION = 2
_IMG_EXTS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp"})


def _image_mtimes(faces_dir: Path) -> dict[str, float]:
    """Return ``{filename: mtime}`` for every image in *faces_dir*."""
    result: dict[str, float] = {}
    if not faces_dir.is_dir():
        return result
    for entry in sorted(faces_dir.iterdir()):
        if entry.is_file() and entry.suffix.lower() in _IMG_EXTS:
            try:
                result[entry.name] = entry.stat().st_mtime
            except OSError:
                pass
    return result


class FaceCache:
    """Load and persist face encodings keyed by image modification times."""

    def __init__(self, faces_dir: Path, cache_path: Path) -> None:
        self.faces_dir = faces_dir
        self.cache_path = cache_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> Optional[tuple[list, list[str]]]:
        """Return ``(encodings, names)`` when cache is fresh, else ``None``.

        ``None`` signals the caller to rebuild encodings from scratch and
        then call :meth:`save`.
        """
        try:
            if not self.cache_path.exists():
                logger.info("Face cache missing — will build on first run.")
                return None
            with self.cache_path.open("rb") as fh:
                data = pickle.load(fh)
            if not isinstance(data, dict):
                return None
            if data.get("version") != _CACHE_VERSION:
                logger.info("Face cache version mismatch — rebuilding.")
                return None
            stored_mtimes: dict[str, float] = data.get("mtimes", {})
            current_mtimes = _image_mtimes(self.faces_dir)
            if stored_mtimes != current_mtimes:
                logger.info("Face images changed — rebuilding cache.")
                return None
            encodings: list = data.get("encodings", [])
            names: list[str] = data.get("names", [])
            if len(encodings) != len(names):
                logger.warning("Face cache corrupt (length mismatch) — rebuilding.")
                return None
            logger.info("Face cache hit: %d face(s) loaded without re-encoding.", len(names))
            return encodings, names
        except Exception as exc:
            logger.debug("Face cache load failed (%s) — rebuilding.", exc)
            return None

    def save(self, encodings: list, names: list[str]) -> None:
        """Atomically persist *encodings* and *names* to the cache file."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": _CACHE_VERSION,
                "mtimes": _image_mtimes(self.faces_dir),
                "encodings": encodings,
                "names": names,
            }
            tmp = self.cache_path.with_suffix(".pkl.tmp")
            with tmp.open("wb") as fh:
                pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
            tmp.replace(self.cache_path)
            logger.info("Face cache saved: %d face(s).", len(names))
        except Exception as exc:
            logger.debug("Face cache save failed (%s).", exc)

    def invalidate(self) -> None:
        """Remove the cache file so the next :meth:`load` triggers a rebuild."""
        try:
            self.cache_path.unlink(missing_ok=True)
        except Exception:
            pass
