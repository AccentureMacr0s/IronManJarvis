"""Rule engine for loading YAML-like rule files and matching incidents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import ds_matrix

TYPE_BY_RULE_NAME = {
    "terraform": "TERRAFORM",
    "gitlab_runner": "CI_FAILURE",
    "aws_ssm": "PERMISSION_DENIED",
    "windows_patch": "GENERAL_FAILURE",
    "powershell": "GENERAL_FAILURE",
    "chef": "GENERAL_FAILURE",
}


@dataclass(frozen=True)
class Rule:
    name: str
    component: str
    keywords: list[str]
    severity: str
    incident_type: str

    @property
    def pattern(self) -> str:
        return " ".join(self.keywords)


def _parse_keywords(raw: str) -> list[str]:
    cleaned = raw.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    return [item.strip().strip("\"'") for item in cleaned.split(",") if item.strip()]


def _parse_rule_file(path: Path) -> Rule:
    payload: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        payload[key.strip()] = value.strip()

    name = payload.get("name", path.stem)
    return Rule(
        name=name,
        component=payload.get("component", "Infrastructure"),
        keywords=_parse_keywords(payload.get("keywords", "")),
        severity=payload.get("severity", "medium"),
        incident_type=payload.get("type", TYPE_BY_RULE_NAME.get(name, "GENERAL_FAILURE")),
    )


def load_rules(rules_dir: Path) -> list[Rule]:
    if not rules_dir.exists() or not rules_dir.is_dir():
        return []
    return sorted((_parse_rule_file(path) for path in rules_dir.glob("*.yml")), key=lambda item: item.name)


def rank_rules(text: str, rules: list[Rule]) -> list[dict]:
    if not rules:
        return []
    pattern_map = {rule.name: rule.pattern for rule in rules}
    ranked = ds_matrix.rank(text, pattern_map)
    by_name = {rule.name: rule for rule in rules}
    return [
        {
            "name": row["name"],
            "score": row["score"],
            "component": by_name[row["name"]].component,
            "severity": by_name[row["name"]].severity,
            "type": by_name[row["name"]].incident_type,
            "pattern": row["pattern"],
        }
        for row in ranked
    ]
