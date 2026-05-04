from __future__ import annotations

import datetime
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from anushka_runtime.config import (
    AUX_MEGA_PORT,
    CAMERA_INDEX,
    CONTROL_FILES,
    ENABLE_MONITORING,
    ENABLE_VISION,
    LEFT_ARM_MEGA_PORT,
    OPENAI_API_KEY,
    RIGHT_ARM_MEGA_PORT,
    STATUS_FILES,
    TTS_ENGINE,
    module_script,
)
from anushka_runtime.ipc import append_message, open_reader, read_available, reset_runtime_state
from Speech.essentialFunctions import speak


SMOKE_TEST = os.getenv("ANUSHKA_SMOKE_TEST", "").strip().lower() in {"1", "true", "yes", "on"}


def _console(message: str) -> None:
    try:
        sys.stderr.write(f"[boss] {message}\n")
        sys.stderr.flush()
    except Exception:
        pass


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    status_key: str
    control_key: str
    optional: bool = False
    startup_timeout: float = 30.0

    @property
    def script(self) -> Path:
        return module_script(self.name)


MODULE_SEQUENCE: list[ModuleSpec] = [
    ModuleSpec("heartbeat", "heartbeat", "heartbeat", optional=True, startup_timeout=10.0),
    ModuleSpec("monitor", "monitor", "monitor", optional=True, startup_timeout=10.0),
    ModuleSpec("auxmega", "auxmega", "auxmega"),
    ModuleSpec("haath", "haath", "haath"),
]

# Vision must come up BEFORE hearing so the greeting engine can grab a frame
# (and so the bot is "watching" before it begins listening for queries).
if ENABLE_VISION:
    MODULE_SEQUENCE.append(ModuleSpec("vision", "vision", "vision", optional=True, startup_timeout=45.0))

MODULE_SEQUENCE.append(ModuleSpec("hear", "hear", "hear"))


def monitor_log(message: str) -> None:
    if ENABLE_MONITORING:
        append_message(CONTROL_FILES["monitor"], f"Log- {message}")


def monitor_error(message: str) -> None:
    if ENABLE_MONITORING:
        append_message(CONTROL_FILES["monitor"], f"Error- {message}")


def wait_for_ready(spec: ModuleSpec, process: subprocess.Popen[str]) -> tuple[bool, str]:
    deadline = time.time() + spec.startup_timeout
    reader = open_reader(STATUS_FILES[spec.status_key])
    try:
        while time.time() < deadline:
            if process.poll() is not None:
                return False, f"{spec.name} exited early with code {process.returncode}."
            message = read_available(reader)
            if message == "1":
                return True, ""
            if message and message != "1":
                monitor_log(f"{spec.name} startup notice: {message}")
                _console(f"{spec.name}: {message}")
            time.sleep(0.1)
        return False, f"{spec.name} did not report ready within {spec.startup_timeout:.0f} seconds."
    finally:
        reader.close()


def launch_module(spec: ModuleSpec) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, str(spec.script)],
        cwd=str(spec.script.parent),
    )


def shutdown_modules(processes: dict[str, subprocess.Popen[str]]) -> None:
    shutdown_order = ["vision", "hear", "haath", "auxmega", "monitor", "heartbeat"]
    wait_timeouts = {
        "hear": 20,
    }
    for name in shutdown_order:
        if name in CONTROL_FILES:
            append_message(CONTROL_FILES[name], "-1")

    for name, process in processes.items():
        try:
            process.wait(timeout=wait_timeouts.get(name, 5))
        except subprocess.TimeoutExpired:
            _console(f"{name} did not exit cleanly; sending SIGINT.")
            try:
                process.send_signal(signal.SIGINT)
                process.wait(timeout=3)
                continue
            except (subprocess.TimeoutExpired, ProcessLookupError):
                pass

            _console(f"{name} still alive; sending SIGTERM.")
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                _console(f"{name} unresponsive; killing.")
                process.kill()


def _run_early_greeting() -> bool:
    """Try to greet whoever is in front of the camera using offline TTS.

    Returns ``True`` if a greeting (personalised or generic) was actually
    spoken, so the caller can skip a fallback "Ready to listen" line.
    """
    try:
        from Vision.greeting_engine import get_default_engine
    except Exception as exc:
        _console(f"Greeting engine import failed ({exc!s}).")
        return False

    try:
        engine = get_default_engine()
    except Exception as exc:
        _console(f"Greeting engine init failed ({exc!s}).")
        return False

    if not engine.ready:
        _console("Greeting engine not ready (no faces or vision libs).")
        return False

    try:
        result = engine.greet_if_person_in_frame(
            camera_index=CAMERA_INDEX,
            speak_fn=speak,
        )
    except Exception as exc:
        _console(f"Greeting attempt failed ({exc!s}).")
        return False

    if result is None:
        return False
    name, _line = result
    _console(f"Greeted {name}.")
    return True


def _print_startup_summary() -> None:
    _console("---- Anushka runtime starting ----")
    _console(f"OpenAI key configured: {bool(OPENAI_API_KEY)}")
    _console(f"TTS engine: {TTS_ENGINE}")
    _console(f"Vision enabled: {ENABLE_VISION}, Monitoring enabled: {ENABLE_MONITORING}")
    _console(
        "Serial ports — left arm: {l}, right arm: {r}, aux: {a}".format(
            l=LEFT_ARM_MEGA_PORT or "(sim)",
            r=RIGHT_ARM_MEGA_PORT or "(sim)",
            a=AUX_MEGA_PORT or "(sim)",
        )
    )
    if SMOKE_TEST:
        _console("ANUSHKA_SMOKE_TEST=on: orchestrator will exit after all modules report ready.")


def main() -> None:
    _print_startup_summary()
    reset_runtime_state()
    append_message(CONTROL_FILES["boss"], "")
    append_message(CONTROL_FILES["monitor"], f"StartTime- {datetime.datetime.now().isoformat(timespec='seconds')}")

    if not SMOKE_TEST:
        try:
            speak("Initiating all modules.")
        except Exception as exc:
            _console(f"Initial speech failed: {exc!s}")

    greeting_done = False

    processes: dict[str, subprocess.Popen[str]] = {}
    started: list[str] = []
    failure_message = ""

    try:
        for spec in MODULE_SEQUENCE:
            # Vision-first greeting: run it BEFORE the vision subprocess takes
            # the camera. If vision is disabled, the greeting still fires once
            # before hearing starts (handled below).
            if spec.name == "vision" and not greeting_done and not SMOKE_TEST:
                greeting_done = _run_early_greeting()

            if spec.name == "hear" and not greeting_done and not SMOKE_TEST:
                try:
                    speak("Ready to listen.")
                except Exception:
                    pass
                greeting_done = True

            _console(f"Launching {spec.name}…")
            process = launch_module(spec)
            processes[spec.name] = process
            ok, error = wait_for_ready(spec, process)
            if not ok:
                if spec.optional:
                    monitor_error(error)
                    _console(f"Optional module skipped: {error}")
                    continue
                failure_message = error
                monitor_error(error)
                _console(f"FATAL: {error}")
                break
            started.append(spec.name)
            monitor_log(f"{spec.name} module is active and running.")
            _console(f"{spec.name} ready.")

        if failure_message:
            try:
                speak(failure_message)
            except Exception:
                pass
            return

        if not SMOKE_TEST:
            try:
                speak("All the configured systems are now running.")
            except Exception:
                pass

        if SMOKE_TEST:
            _console("Smoke test complete: all modules reported ready.")
            return

        boss_reader = open_reader(CONTROL_FILES["boss"])
        try:
            while True:
                command = read_available(boss_reader)
                if command == "-1":
                    break
                for name, process in list(processes.items()):
                    if process.poll() is not None:
                        message = f"{name} stopped unexpectedly."
                        monitor_error(message)
                        _console(message)
                        if name in {"hear", "haath", "auxmega"}:
                            failure_message = message
                            break
                if failure_message:
                    break
                time.sleep(0.2)
        finally:
            boss_reader.close()

        if failure_message:
            try:
                speak(failure_message)
            except Exception:
                pass
    finally:
        shutdown_modules(processes)
        append_message(CONTROL_FILES["monitor"], f"StopTime- {datetime.datetime.now().isoformat(timespec='seconds')}")
        if not SMOKE_TEST:
            try:
                speak("All the systems have now been turned down. Goodbye and have a great day.")
            except Exception:
                pass
        _console("Shutdown complete.")


if __name__ == "__main__":
    main()
