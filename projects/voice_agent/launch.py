#!/usr/bin/env python3
"""Launcher for voice-agent project split."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENTRYPOINT = ROOT / "dima_6_stark_mode_chat" / "main.py"


def main() -> int:
    entrypoint = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_ENTRYPOINT
    if not entrypoint.exists():
        print(f"Voice entrypoint not found: {entrypoint}")
        return 2

    proc = subprocess.run([sys.executable, str(entrypoint)], cwd=str(entrypoint.parent))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
