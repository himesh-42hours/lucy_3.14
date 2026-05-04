from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Iterable

from .config import REPO_ROOT, SEAN_ROOT


def bootstrap_paths() -> None:
    deps_root = REPO_ROOT / ".deps"
    for entry in (str(REPO_ROOT), str(SEAN_ROOT), str(deps_root)):
        if entry not in sys.path:
            sys.path.insert(0, entry)


def run_python_script(script: Path, args: Iterable[str] = ()) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, str(script), *list(args)],
        cwd=str(script.parent),
    )
