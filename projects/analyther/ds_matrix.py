"""DSMatrix weighted semantic ranking without embeddings."""

from __future__ import annotations

from . import mirror_parser


def score_tokens(text_tokens: list[str], pattern_tokens: list[str]) -> float:
    if not pattern_tokens:
        return 0.0
    common = len(set(text_tokens) & set(pattern_tokens))
    return common / len(set(pattern_tokens))


def score(text: str, pattern: str) -> float:
    return score_tokens(mirror_parser.extract(text), mirror_parser.extract(pattern))


def rank(text: str, rules: dict[str, str]) -> list[dict]:
    text_tokens = mirror_parser.extract(text)
    ranked = []
    for name, pattern in rules.items():
        pattern_tokens = mirror_parser.extract(pattern)
        ranked.append(
            {
                "name": name,
                "score": round(score_tokens(text_tokens, pattern_tokens), 4),
                "pattern": pattern,
            }
        )
    return sorted(ranked, key=lambda item: item["score"], reverse=True)
