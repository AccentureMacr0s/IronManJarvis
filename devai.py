#!/usr/bin/env python3
"""Backward-compatible entrypoint for the split analyther project."""

from projects.analyther.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
