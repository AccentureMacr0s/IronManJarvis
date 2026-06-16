"""Repository context scanner for analyzer ranking hints."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

HINTS = {
    "terraform": "Terraform",
    "gitlab": "CI/CD",
    "runner": "CI/CD",
    "powershell": "Windows Automation",
    "ssm": "AWS SSM",
}


def scan(root: Path, max_files: int = 400) -> dict:
    extension_counter: Counter[str] = Counter()
    component_counter: Counter[str] = Counter()
    scanned = 0

    for path in root.rglob("*"):
        if scanned >= max_files:
            break
        if not path.is_file():
            continue
        scanned += 1
        extension_counter[path.suffix.lower() or "<none>"] += 1
        lowered = str(path.relative_to(root)).lower()
        for hint, component in HINTS.items():
            if hint in lowered:
                component_counter[component] += 1

    return {
        "root": str(root),
        "scanned_files": scanned,
        "top_extensions": [{"ext": ext, "count": count} for ext, count in extension_counter.most_common(5)],
        "dominant_components": [name for name, _ in component_counter.most_common(3)],
    }
