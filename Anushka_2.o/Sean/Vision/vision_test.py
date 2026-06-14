"""Live camera vision test for Anooshka.

Run standalone to verify the full vision stack against the real camera:
  python Sean/Vision/vision_test.py

Controls
--------
  Q / Esc  — quit
  F        — freeze / unfreeze frame
  R        — reset temporal vote buffer and re-enable greeting
  S        — save current frame as PNG to Vision/test_snapshots/
  1        — mode: face recognition  (default)
  2        — mode: blur / brightness meters only
  3        — mode: pose skeleton

Display
-------
  Top-left panel:   live mode, FPS, frame quality (blur / brightness)
  Face bbox:        name + distance + vote count / threshold
  Bottom bar:       temporal vote buffer  (last 10 readings, colour-coded)
  Right panel:      known faces list + unknown embedding count
"""
from __future__ import annotations

import collections
import datetime
import os
import sys
import time
from pathlib import Path

# ── Path bootstrap (mirrors vision_controller.py) ────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for _e in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if _e not in sys.path:
        sys.path.insert(0, _e)

# ── Vision imports ────────────────────────────────────────────────────────────
try:
    import cv2
    import numpy as np
    import face_recognition
    import insightface
except ImportError as exc:
    sys.exit(f"[vision_test] Required library missing: {exc}\n"
             "Install opencv-python, face_recognition, cvzone and try again.")

from anushka_runtime.config import CAMERA_NAME_HINT, CAMERA_SOURCE
from Vision.face_cache import FaceCache
from Vision.profile_store import canonical_display_name

FACES_DIR   = SEAN_ROOT / "Vision" / "faces"
CACHE_PATH  = SEAN_ROOT / "Vision" / "face_cache.pkl"
SNAP_DIR    = SEAN_ROOT / "Vision" / "test_snapshots"

# ── Quality thresholds (must match vision_controller.py) ─────────────────────
_BLUR_THRESHOLD    = 80.0
_DARK_THRESHOLD    = 30.0
_TINY_FACE_MIN_PX  = 50
_VOTE_MAXLEN       = 10
_VOTE_THRESHOLD    = 7
_FACE_DIST_THRESH  = 0.48

# ── Colours (BGR) ────────────────────────────────────────────────────────────
C_GREEN  = (0, 220, 60)
C_RED    = (0, 50, 220)
C_YELLOW = (0, 200, 220)
C_BLUE   = (220, 120, 0)
C_WHITE  = (240, 240, 240)
C_GREY   = (120, 120, 120)
C_BLACK  = (0, 0, 0)
C_ORANGE = (0, 140, 255)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _laplacian_var(frame) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _mean_brightness(frame) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def _bar(img, x: int, y: int, w: int, h: int,
         value: float, max_val: float,
         good_thresh: float, label: str, colour_ok, colour_bad) -> None:
    """Draw a filled progress bar with label."""
    ratio = min(1.0, max(0.0, value / max_val))
    fill  = int(w * ratio)
    colour = colour_ok if value >= good_thresh else colour_bad
    cv2.rectangle(img, (x, y), (x + w, y + h), C_GREY, 1)
    cv2.rectangle(img, (x, y), (x + fill, y + h), colour, -1)
    cv2.putText(img, f"{label}: {value:.0f}", (x + 4, y + h - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_WHITE, 1, cv2.LINE_AA)


def _txt(img, text: str, x: int, y: int,
         scale: float = 0.5, colour=C_WHITE, thickness: int = 1) -> None:
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                scale, colour, thickness, cv2.LINE_AA)


def _load_encodings() -> tuple[list, list[str]]:
    fc = FaceCache(FACES_DIR, CACHE_PATH)
    cached = fc.load()
    if cached:
        print(f"[vision_test] Cache hit: {len(cached[1])} face(s).")
        return cached
    print("[vision_test] Building encodings from images…")
    encodings, names = [], []
    if FACES_DIR.is_dir():
        for f in sorted(FACES_DIR.iterdir()):
            if f.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
                continue
            img = cv2.imread(str(f))
            if img is None:
                continue
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encs = face_recognition.face_encodings(rgb)
            if encs:
                encodings.append(encs[0])
                names.append(f.stem)
    if encodings:
        fc.save(encodings, names)
    print(f"[vision_test] Encoded {len(names)} face(s).")
    return encodings, names


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load known faces ──────────────────────────────────────────────────────
    known_encodings, known_names = _load_encodings()

    # ── Open camera ──────────────────────────────────────────────────────────
    cam_src = CAMERA_SOURCE
    print(f"[vision_test] Opening camera: {cam_src!r}"
          + (f" (hint: {CAMERA_NAME_HINT})" if CAMERA_NAME_HINT else ""))
    cap = cv2.VideoCapture(cam_src)
    if not cap.isOpened():
        sys.exit(f"[vision_test] Could not open camera {cam_src!r}.")
    try:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    except Exception:
        pass
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  800)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)

    yunet = cv2.FaceDetectorYN.create(
    str(SEAN_ROOT / "Vision" / "models" / "face_detection_yunet_2023mar.onnx"),
    "",
    (800, 600)
    )

    # ── State ─────────────────────────────────────────────────────────────────
    vote_buffer: collections.deque[str | None] = collections.deque(maxlen=_VOTE_MAXLEN)
    confirmed_identity: str | None = None
    unknown_count    = 0
    greeted_set: set[str] = set()
    frozen           = False
    frozen_frame     = None
    display_mode     = 1       # 1=recognition, 2=quality-only, 3=pose

    fps_times: collections.deque[float] = collections.deque(maxlen=30)

    print("[vision_test] Window open — Q/Esc to quit, F freeze, R reset, S snapshot, 1/2/3 mode.")

    while True:
        # ── Frame capture ────────────────────────────────────────────────────
        if not frozen:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue
        else:
            frame = frozen_frame.copy()

        now = time.time()
        fps_times.append(now)
        fps = len(fps_times) / max(1e-6, fps_times[-1] - fps_times[0]) if len(fps_times) > 1 else 0.0

        # ── Quality metrics ──────────────────────────────────────────────────
        blur_val  = _laplacian_var(frame)
        bright_val = _mean_brightness(frame)
        is_blurry = blur_val  < _BLUR_THRESHOLD
        is_dark   = bright_val < _DARK_THRESHOLD

        canvas = frame.copy()
        h, w   = canvas.shape[:2]

        # ── Mode 1: face recognition ─────────────────────────────────────────
        if display_mode == 1 and not is_blurry and not is_dark:
            yunet.setInputSize((w, h))

            _, detections = yunet.detect(frame)

            bboxs = []

            if detections is not None:

                for det in detections:

                    x, y, bw, bh = map(
                        int,
                        det[:4]
                    )

                    score = float(det[-1])

                    bboxs.append({
                        "score": score,
                        "bbox": (
                            x,
                            y,
                            bw,
                            bh
                        )
                    })

            frame_reading: str | None = None

            if bboxs:
                for bbox in bboxs:
                    score = int(bbox["score"] * 100)
                    bx, by, bw, bh = bbox["bbox"]
                    tiny = bw < _TINY_FACE_MIN_PX or bh < _TINY_FACE_MIN_PX

                    # Crop with padding
                    x1 = max(0, bx - 40)
                    y1 = max(0, by - 40)
                    x2 = min(w, bx + bw + 40)
                    y2 = min(h, by + bh + 40)
                    mu = frame[y1:y2, x1:x2]
                    mu_rgb = cv2.cvtColor(mu, cv2.COLOR_BGR2RGB)

                    label      = "?"
                    dist_label = ""
                    box_colour = C_GREY

                    if score >= 94 and not tiny:
                        try:
                            encs = face_recognition.face_encodings(mu_rgb)
                            if encs:
                                enc      = encs[0]
                                dists    = face_recognition.face_distance(known_encodings, enc)
                                idx      = int(np.argmin(dists)) if len(dists) else -1
                                best_d   = float(dists[idx]) if idx >= 0 else 1.0
                                matched  = idx >= 0 and best_d <= _FACE_DIST_THRESH

                                if matched:
                                    raw_name     = known_names[idx]
                                    label        = canonical_display_name(raw_name)
                                    dist_label   = f"d={best_d:.3f}"
                                    box_colour   = C_GREEN
                                    frame_reading = raw_name
                                elif idx >= 0 and best_d <= 0.52:
                                    label        = f"~{canonical_display_name(known_names[idx])}"
                                    dist_label   = f"d={best_d:.3f} (soft)"
                                    box_colour   = C_YELLOW
                                    frame_reading = None
                                else:
                                    label        = "Unknown"
                                    dist_label   = f"d={best_d:.3f}"
                                    box_colour   = C_RED
                                    frame_reading = None
                        except Exception:
                            label = "err"
                    elif tiny:
                        label      = "Too small"
                        box_colour = C_ORANGE
                    else:
                        label      = f"Low conf ({score}%)"
                        box_colour = C_GREY

                    # Draw bbox
                    cv2.rectangle(canvas, (bx, by), (bx + bw, by + bh), box_colour, 2)
                    _txt(canvas, label,       bx,      by - 22, 0.55, box_colour, 2)
                    _txt(canvas, dist_label,  bx,      by - 6,  0.4,  C_WHITE)
                    _txt(canvas, f"conf={score}%", bx, by + bh + 14, 0.38, C_GREY)

            # ── Temporal vote ─────────────────────────────────────────────────
            vote_buffer.append(frame_reading)
            counts: dict[str | None, int] = {}
            for v in vote_buffer:
                counts[v] = counts.get(v, 0) + 1
            best_key  = max(counts, key=lambda k: counts[k]) if counts else None
            best_count = counts.get(best_key, 0)
            if best_count >= _VOTE_THRESHOLD and best_key != confirmed_identity:
                confirmed_identity = best_key

            # ── Bottom vote bar ───────────────────────────────────────────────
            bar_y = h - 28
            cv2.rectangle(canvas, (0, bar_y - 4), (w, h), (20, 20, 20), -1)
            cell_w = w // _VOTE_MAXLEN
            for i, v in enumerate(vote_buffer):
                colour = C_GREEN if v is not None else C_RED
                xo = i * cell_w
                cv2.rectangle(canvas, (xo + 2, bar_y), (xo + cell_w - 2, h - 4), colour, -1)
                short = (canonical_display_name(v)[:6] if v else "???")
                _txt(canvas, short, xo + 3, h - 8, 0.32, C_BLACK)

            # Vote progress
            _txt(canvas,
                 f"Vote: {best_count}/{_VOTE_THRESHOLD}  confirmed: {confirmed_identity or 'none'}",
                 4, bar_y - 8, 0.45, C_WHITE)

        # ── Mode 2: quality meters only ──────────────────────────────────────
        elif display_mode == 2:
            pass   # bars drawn below anyway

        # ── Mode 3: pose ─────────────────────────────────────────────────────
        elif display_mode == 3:
            try:
                from cvzone.PoseModule import PoseDetector
                if not hasattr(main, "_pose"):
                    main._pose = PoseDetector()  # type: ignore[attr-defined]
                canvas = main._pose.findPose(canvas)  # type: ignore[attr-defined]
            except Exception as exc:
                _txt(canvas, f"Pose unavailable: {exc}", 10, 60, 0.45, C_RED)

        # ── HUD overlay (all modes) ───────────────────────────────────────────
        # Top-left info panel
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (260, 130), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.55, canvas, 0.45, 0, canvas)

        mode_labels = {1: "Recognition", 2: "Quality", 3: "Pose"}
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        _txt(canvas, f"Anooshka Vision Test  {ts}",    6,  16, 0.48, C_WHITE)
        _txt(canvas, f"Mode [{display_mode}]: {mode_labels.get(display_mode,'?')}",
                                                        6,  34, 0.44, C_BLUE)
        _txt(canvas, f"FPS: {fps:.1f}",                6,  50, 0.44, C_WHITE)
        _txt(canvas, f"Known faces: {len(known_names)}",6, 66, 0.44, C_WHITE)
        _txt(canvas, f"Unknown seen: {unknown_count}",  6,  82, 0.44, C_WHITE)
        if frozen:
            _txt(canvas, "[ FROZEN ]", 6, 100, 0.5, C_ORANGE, 2)

        # Quality bars
        _bar(canvas, 0, 132, 180, 16, blur_val,   300.0, _BLUR_THRESHOLD,
             "Blur", C_GREEN, C_RED)
        _bar(canvas, 0, 152, 180, 16, bright_val, 255.0, _DARK_THRESHOLD,
             "Bright", C_GREEN, C_RED)

        quality_flags = []
        if is_blurry:
            quality_flags.append("BLURRY")
        if is_dark:
            quality_flags.append("DARK")
        if quality_flags:
            _txt(canvas, "  ".join(quality_flags), 6, 188, 0.55, C_RED, 2)

        # Right panel — known faces list
        rx = w - 180
        cv2.rectangle(canvas, (rx - 4, 0), (w, len(known_names) * 18 + 24), (20, 20, 20), -1)
        _txt(canvas, "Known faces:", rx, 16, 0.44, C_YELLOW)
        for i, nm in enumerate(known_names):
            colour = C_GREEN if nm == confirmed_identity else C_WHITE
            _txt(canvas, f"  {canonical_display_name(nm)}", rx, 34 + i * 18, 0.4, colour)

        cv2.imshow("Anooshka Vision Test", canvas)

        # ── Key handling ──────────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q"), 27):   # Q or Esc
            break
        elif key == ord("f") or key == ord("F"):
            frozen = not frozen
            if frozen:
                frozen_frame = frame.copy()
            print(f"[vision_test] Frame {'frozen' if frozen else 'live'}.")
        elif key == ord("r") or key == ord("R"):
            vote_buffer.clear()
            confirmed_identity = None
            greeted_set.clear()
            unknown_count = 0
            print("[vision_test] Vote buffer and greeting state reset.")
        elif key == ord("s") or key == ord("S"):
            ts_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            snap_path = SNAP_DIR / f"snap_{ts_file}.png"
            cv2.imwrite(str(snap_path), canvas)
            print(f"[vision_test] Snapshot saved: {snap_path}")
        elif key == ord("1"):
            display_mode = 1
            print("[vision_test] Mode: face recognition.")
        elif key == ord("2"):
            display_mode = 2
            print("[vision_test] Mode: quality meters.")
        elif key == ord("3"):
            display_mode = 3
            print("[vision_test] Mode: pose skeleton.")

    cap.release()
    cv2.destroyAllWindows()
    print("[vision_test] Exited.")


if __name__ == "__main__":
    main()
