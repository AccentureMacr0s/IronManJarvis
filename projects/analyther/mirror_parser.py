"""Mirror parser layer for fast text normalization and token extraction."""

from __future__ import annotations

import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]+")


def extract(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def extract_from_lines(lines: list[str]) -> list[str]:
    return [token for line in lines for token in extract(line)]


def top_terms(tokens: list[str], limit: int = 8) -> list[str]:
    return [token for token, _ in Counter(tokens).most_common(limit)]
