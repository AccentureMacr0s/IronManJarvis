#!/usr/bin/env python3
"""devai CLI MVP: log analysis, repo search, and Jira ticket draft generation."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

CRITICAL_PATTERNS = {
    "CI_FAILURE": [r"\bci\b", r"pipeline", r"runner", r"job failed"],
    "PERMISSION_DENIED": [r"permission denied", r"access denied", r"forbidden", r"\beacces\b"],
    "TIMEOUT": [r"timeout", r"timed out", r"deadline exceeded"],
    "TERRAFORM": [r"terraform", r"\bresource\b", r"plan failed", r"apply failed"],
    "NETWORK": [r"connection refused", r"dns", r"network", r"reset by peer"],
    "TEST_FAILURE": [r"test failed", r"assert", r"pytest", r"unittest", r"spec failed"],
    "BUILD_FAILURE": [r"build failed", r"compilation", r"compile error", r"linker"],
}

CRITICAL_LINE_RE = re.compile(
    r"(error|fail(?:ed)?|exception|denied|timeout|traceback|fatal)",
    re.IGNORECASE,
)

FIND_PATTERNS = [".gitlab-ci.yml", "terraform/**/*.tf", "**/*.sh", "**/*.py", "**/*.yml", "**/*.yaml"]


class DeVAIError(Exception):
    """Base command error."""


def _read_lines(file_path: Path) -> list[str]:
    if not file_path.exists():
        raise DeVAIError(f"File not found: {file_path}")
    if not file_path.is_file():
        raise DeVAIError(f"Not a file: {file_path}")
    return file_path.read_text(encoding="utf-8", errors="ignore").splitlines()


def _classify_line(line: str) -> str:
    line_lower = line.lower()
    for label, patterns in CRITICAL_PATTERNS.items():
        if any(re.search(pattern, line_lower, re.IGNORECASE) for pattern in patterns):
            return label
    return "GENERAL_FAILURE"


def analyze_logs(file_path: Path, limit: int = 50) -> dict:
    lines = _read_lines(file_path)
    critical_entries: list[tuple[int, str, str]] = []

    for line_num, line in enumerate(lines, start=1):
        if CRITICAL_LINE_RE.search(line):
            failure_type = _classify_line(line)
            critical_entries.append((line_num, failure_type, line.strip()))

    latest_entries = critical_entries[-limit:]
    grouped = Counter(entry[1] for entry in latest_entries)

    component = detect_component(file_path, latest_entries)
    probable_cause = latest_entries[-1][2] if latest_entries else "No critical issue detected"

    return {
        "file": str(file_path),
        "total_lines": len(lines),
        "critical_count": len(critical_entries),
        "latest_critical": [
            {"line": line_num, "type": failure_type, "text": text}
            for line_num, failure_type, text in latest_entries
        ],
        "grouped_by_type": dict(grouped),
        "primary_type": grouped.most_common(1)[0][0] if grouped else "NO_FAILURE",
        "component": component,
        "probable_cause": probable_cause,
    }


def detect_component(file_path: Path, entries: Iterable[tuple[int, str, str]]) -> str:
    stem = file_path.name.lower()
    if "terraform" in stem:
        return "Terraform"
    if "gitlab" in stem or "pipeline" in stem or "runner" in stem:
        return "CI/CD"

    text = " ".join(item[2].lower() for item in entries)
    if "terraform" in text:
        return "Terraform"
    if any(token in text for token in ["gitlab", "runner", "pipeline", "job"]):
        return "CI/CD"
    if any(token in text for token in ["kubernetes", "k8s", "helm"]):
        return "Kubernetes"
    return "Infrastructure"


def command_logs(args: argparse.Namespace) -> int:
    result = analyze_logs(Path(args.file).expanduser().resolve(), limit=args.limit)
    print(f"File: {result['file']}")
    print(f"Total lines: {result['total_lines']}")
    print(f"Critical matches: {result['critical_count']}")
    print(f"Primary type: {result['primary_type']}")
    print("\nGrouped by type:")
    if result["grouped_by_type"]:
        for failure_type, count in sorted(result["grouped_by_type"].items(), key=lambda item: item[1], reverse=True):
            print(f"- {failure_type}: {count}")
    else:
        print("- none")

    print("\nLatest critical lines:")
    if result["latest_critical"]:
        for entry in result["latest_critical"]:
            print(f"[{entry['line']}] ({entry['type']}) {entry['text']}")
    else:
        print("- none")

    if args.json:
        print("\nJSON:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _tokenize_query(query: str) -> list[str]:
    return [token for token in re.split(r"\W+", query.lower()) if token]


def find_matches(root: Path, query: str, limit: int = 25) -> list[dict]:
    query_lower = query.lower()
    query_tokens = _tokenize_query(query)
    candidates: set[Path] = set()

    for pattern in FIND_PATTERNS:
        candidates.update(root.glob(pattern))

    results = []
    for path in candidates:
        if not path.is_file():
            continue
        rel_path = path.relative_to(root)
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        for index, line in enumerate(lines, start=1):
            line_lower = line.lower()
            if query_lower not in line_lower and not all(token in line_lower for token in query_tokens):
                continue

            token_hits = sum(line_lower.count(token) for token in query_tokens)
            path_bonus = 3 if "terraform" in str(rel_path).lower() else 0
            ci_bonus = 3 if ".gitlab-ci" in str(rel_path).lower() else 0
            exact_bonus = 5 if query_lower in line_lower else 0
            score = token_hits + path_bonus + ci_bonus + exact_bonus

            start = max(0, index - 2)
            end = min(len(lines), index + 1)
            context = "\n".join(lines[start:end])

            results.append(
                {
                    "path": str(rel_path),
                    "line": index,
                    "score": score,
                    "match": line.strip(),
                    "context": context,
                }
            )

    return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]


def command_find(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise DeVAIError(f"Search root is invalid: {root}")

    results = find_matches(root, args.query, limit=args.limit)

    print(f"Query: {args.query}")
    print(f"Root: {root}")
    print(f"Matches: {len(results)}")

    if not results:
        print("No matches found in targeted files.")
        return 0

    print()
    for item in results:
        print(f"{item['path']}:{item['line']}  score={item['score']}")
        print(f"  {item['match']}")
    return 0


def generate_jira_ticket(file_path: Path, limit: int = 50) -> str:
    analysis = analyze_logs(file_path, limit=limit)
    primary_type = analysis["primary_type"]
    component = analysis["component"]
    error = analysis["probable_cause"]

    impact = "Pipeline is unstable and blocks delivery." if primary_type != "NO_FAILURE" else "No blocker identified."
    repro_steps = [
        f"Open log file: {analysis['file']}",
        "Run the failing pipeline/job again to confirm reproducibility.",
        f"Observe error pattern: {primary_type}",
    ]

    proposed_fix = {
        "PERMISSION_DENIED": "Validate credentials/permissions for the failing job and secrets scope.",
        "TIMEOUT": "Increase timeout and optimize the slow step; check external dependency latency.",
        "TERRAFORM": "Run terraform validate/plan locally and inspect provider/resource configuration.",
        "CI_FAILURE": "Inspect the failing CI job stage and runner configuration.",
        "NETWORK": "Verify network reachability, DNS, and firewall/security group settings.",
        "TEST_FAILURE": "Fix failing tests or update flaky test handling and environment setup.",
        "BUILD_FAILURE": "Review compiler/build logs and align dependencies/toolchain versions.",
        "GENERAL_FAILURE": "Inspect full stack trace and narrow down the first failing operation.",
        "NO_FAILURE": "No action required.",
    }.get(primary_type, "Inspect full logs and resolve root cause.")

    return "\n".join(
        [
            f"Title: [{primary_type}] {component} pipeline issue",
            f"Type: {primary_type}",
            f"Component: {component}",
            f"Error: {error}",
            f"Impact: {impact}",
            "Steps to Reproduce:",
            *[f"- {step}" for step in repro_steps],
            f"Proposed Fix: {proposed_fix}",
        ]
    )


def command_jira_from_log(args: argparse.Namespace) -> int:
    ticket = generate_jira_ticket(Path(args.file).expanduser().resolve(), limit=args.limit)
    print(ticket)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devai",
        description="DevAI MVP CLI: logs analysis, repository find, and Jira draft generation.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    logs_parser = subparsers.add_parser("logs", help="Analyze log file and summarize critical errors")
    logs_parser.add_argument("file", help="Path to log file")
    logs_parser.add_argument("--limit", type=int, default=50, help="Number of latest critical entries to include")
    logs_parser.add_argument("--json", action="store_true", help="Print JSON payload in addition to summary")
    logs_parser.set_defaults(func=command_logs)

    find_parser = subparsers.add_parser("find", help="Search repository files with simple relevance scoring")
    find_parser.add_argument("query", help="Search query")
    find_parser.add_argument("--root", default=".", help="Repository root path")
    find_parser.add_argument("--limit", type=int, default=25, help="Max number of results")
    find_parser.set_defaults(func=command_find)

    jira_parser = subparsers.add_parser("jira-from-log", help="Generate Jira ticket draft from a log file")
    jira_parser.add_argument("file", help="Path to log file")
    jira_parser.add_argument("--limit", type=int, default=50, help="Number of latest critical entries to inspect")
    jira_parser.set_defaults(func=command_jira_from_log)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except DeVAIError as exc:
        parser.exit(status=2, message=f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
