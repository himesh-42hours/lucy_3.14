from __future__ import annotations

import datetime
import json
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SEAN_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = REPO_ROOT / ".deps"
for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(DEPS_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import requests

from anushka_runtime.config import CONTROL_FILES, ENABLE_MONITORING, LOG_FILES, MONITOR_URL, STATUS_FILES
from anushka_runtime.ipc import append_message, open_reader, read_available

REMOTE_AVAILABLE = False


def _post(endpoint: str, text: str, method: str = "post") -> None:
    if not ENABLE_MONITORING or not REMOTE_AVAILABLE:
        return
    url = f"{MONITOR_URL}/{endpoint.lstrip('/')}"
    payload = {"text": text}
    headers = {"Content-Type": "application/json"}
    request_fn = getattr(requests, method)
    request_fn(url, data=json.dumps(payload), headers=headers, timeout=5)


def _upload_conversation_log() -> None:
    if not ENABLE_MONITORING or not REMOTE_AVAILABLE:
        return
    source = LOG_FILES["conversation"]
    if not source.exists() or not source.read_text(encoding="utf-8").strip():
        return
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archived = source.with_name(f"file_{timestamp}.txt")
    os.replace(source, archived)
    try:
        with archived.open("rb") as handle:
            response = requests.post(f"{MONITOR_URL}/convo-log/", files={"file": handle}, timeout=10)
        if response.ok:
            archived.unlink(missing_ok=True)
    except Exception:
        pass


def main() -> None:
    global REMOTE_AVAILABLE
    if ENABLE_MONITORING:
        try:
            requests.get(f"{MONITOR_URL}/test/", timeout=5)
            REMOTE_AVAILABLE = True
        except Exception:
            REMOTE_AVAILABLE = False
            append_message(STATUS_FILES["monitor"], "Remote monitor unavailable. Running with local logs only.")

    append_message(STATUS_FILES["monitor"], "1")

    reader = open_reader(CONTROL_FILES["monitor"])
    try:
        while True:
            text = read_available(reader)
            if not text:
                time.sleep(0.1)
                continue
            if text == "-1":
                break
            try:
                if text.startswith("Error- "):
                    _post("error/", text.replace("Error- ", ""), "post")
                elif text.startswith("Log- "):
                    _post("log/", text.replace("Log- ", ""), "post")
                elif text.startswith("StartTime- "):
                    _post("start-time/", text.replace("StartTime- ", ""), "put")
                elif text.startswith("StopTime- "):
                    _post("stop-time/", text.replace("StopTime- ", ""), "put")
                elif text.startswith("LastSeen- "):
                    _post("last-seen/", text.replace("LastSeen- ", ""), "put")
                elif text.startswith("Battery- "):
                    _post("battery/", text.replace("Battery- ", ""), "put")
                elif text.startswith("PrintJob- "):
                    _post("print-job/", text.replace("PrintJob- ", ""), "post")
            except Exception:
                append_message(STATUS_FILES["monitor"], "An error occurred while talking to the monitor service. Falling back to local logs.")
                break
    finally:
        _upload_conversation_log()
        append_message(STATUS_FILES["monitor"], "2")
        reader.close()


if __name__ == "__main__":
    main()
