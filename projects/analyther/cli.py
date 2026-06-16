#!/usr/bin/env python3
"""Analyther CLI: log analysis, repo search, and Jira story generation."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from . import mirror_parser, repo_context, rule_engine

CRITICAL_PATTERNS = {
    "CI_FAILURE": [r"\bci\b", r"pipeline", r"runner", r"job failed"],
    "PERMISSION_DENIED": [r"permission denied", r"access denied", r"forbidden", r"\beacces\b"],
    "TIMEOUT": [r"timeout", r"timed out", r"deadline exceeded"],
    "TERRAFORM": [r"terraform", r"\bresource\b", r"plan failed", r"apply failed"],
    "NETWORK": [r"connection refused", r"dns", r"network", r"reset by peer"],
    "TEST_FAILURE": [r"test failed", r"assert", r"pytest", r"unittest", r"spec failed"],
    "BUILD_FAILURE": [r"build failed", r"compilation", r"compile error", r"linker"],
}

SEVERITY_BY_TYPE = {
    "PERMISSION_DENIED": "high",
    "TIMEOUT": "medium",
    "TERRAFORM": "high",
    "CI_FAILURE": "high",
    "NETWORK": "medium",
    "TEST_FAILURE": "medium",
    "BUILD_FAILURE": "high",
    "GENERAL_FAILURE": "medium",
    "NO_FAILURE": "low",
}

CRITICAL_LINE_RE = re.compile(
    r"(error|fail(?:ed)?|exception|denied|timeout|traceback|fatal)",
    re.IGNORECASE,
)

FIND_PATTERNS = [
    ".gitlab-ci.yml",
    "terraform/**/*.tf",
    "**/*.sh",
    "**/*.rb",
    "**/*.py",
    "**/*.yml",
    "**/*.yaml",
]

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


class DeVAIError(Exception):
    """Base command error."""


@lru_cache(maxsize=1)
def _loaded_rules() -> tuple[rule_engine.Rule, ...]:
    return tuple(rule_engine.load_rules(RULES_DIR))


def _rank_with_dsmatrix(lines: list[str]) -> list[dict]:
    return rule_engine.rank_rules("\n".join(lines), list(_loaded_rules()))


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
    if any(token in text for token in ["ssm", "patch", "windows", "powershell"]):
        return "Patch Management"
    if any(token in text for token in ["kubernetes", "k8s", "helm"]):
        return "Kubernetes"
    return "Infrastructure"


def build_structured_event(
    source: str,
    component: str,
    entries: list[tuple[int, str, str]],
    ranked_rules: list[dict],
    top_terms: list[str],
    context_snapshot: dict,
) -> dict:
    grouped = Counter(entry[1] for entry in entries)
    primary_type = grouped.most_common(1)[0][0] if grouped else "NO_FAILURE"
    top_rule = ranked_rules[0] if ranked_rules else None
    if top_rule and top_rule["score"] >= 0.45:
        component = top_rule["component"]
        if primary_type == "NO_FAILURE":
            primary_type = top_rule["type"]

    severity = SEVERITY_BY_TYPE.get(primary_type, "medium")
    if top_rule and top_rule["score"] >= 0.45:
        severity = top_rule["severity"]

    return {
        "type": primary_type,
        "component": component,
        "severity": severity,
        "matches": len(entries),
        "evidence": [
            {"line": line_num, "type": failure_type, "text": text}
            for line_num, failure_type, text in entries
        ],
        "source": source,
        "grouped_by_type": dict(grouped),
        "error": entries[-1][2] if entries else "No critical issue detected",
        "root_cause": top_rule["name"] if top_rule and top_rule["score"] > 0 else "unknown",
        "mirror_terms": top_terms,
        "dsmatrix": ranked_rules[:3],
        "repo_context": context_snapshot,
    }


def analyze_logs(file_path: Path, limit: int = 50) -> dict:
    lines = _read_lines(file_path)
    critical_entries: list[tuple[int, str, str]] = []

    for line_num, line in enumerate(lines, start=1):
        if CRITICAL_LINE_RE.search(line):
            failure_type = _classify_line(line)
            critical_entries.append((line_num, failure_type, line.strip()))

    latest_entries = critical_entries[-limit:]
    component = detect_component(file_path, latest_entries)
    ranked_rules = _rank_with_dsmatrix(lines)
    mirror_terms = mirror_parser.top_terms(mirror_parser.extract_from_lines(lines))
    context_snapshot = repo_context.scan(Path.cwd())
    structured = build_structured_event(
        str(file_path),
        component,
        latest_entries,
        ranked_rules,
        mirror_terms,
        context_snapshot,
    )

    return {
        "file": str(file_path),
        "total_lines": len(lines),
        "critical_count": len(critical_entries),
        "structured": structured,
    }


def _collect_context_lines(context: str, attachments: list[Path]) -> list[str]:
    lines: list[str] = []
    if context:
        lines.extend(context.splitlines())

    for attachment in attachments:
        if not attachment.exists() or not attachment.is_file():
            raise DeVAIError(f"Attachment file not found: {attachment}")
        text = attachment.read_text(encoding="utf-8", errors="ignore")
        lines.extend(text.splitlines()[:200])
    return lines


def analyze_context(context: str, attachments: list[Path], limit: int = 50) -> dict:
    lines = _collect_context_lines(context, attachments)
    critical_entries: list[tuple[int, str, str]] = []

    for line_num, line in enumerate(lines, start=1):
        if CRITICAL_LINE_RE.search(line):
            failure_type = _classify_line(line)
            critical_entries.append((line_num, failure_type, line.strip()))

    latest_entries = critical_entries[-limit:]
    component = detect_component(Path("context_input.txt"), latest_entries)

    if attachments and component == "Infrastructure":
        attachment_names = " ".join(path.name.lower() for path in attachments)
        if "terraform" in attachment_names or any(path.suffix == ".tf" for path in attachments):
            component = "Terraform"
        elif any("gitlab" in path.name.lower() for path in attachments):
            component = "CI/CD"

    ranked_rules = _rank_with_dsmatrix(lines)
    mirror_terms = mirror_parser.top_terms(mirror_parser.extract_from_lines(lines))
    context_snapshot = repo_context.scan(Path.cwd())
    structured = build_structured_event(
        "context+attachments",
        component,
        latest_entries,
        ranked_rules,
        mirror_terms,
        context_snapshot,
    )

    return {
        "file": "context+attachments",
        "total_lines": len(lines),
        "critical_count": len(critical_entries),
        "structured": structured,
    }


def render_jira_template(analysis: dict) -> str:
    structured = analysis["structured"]

    impact = "Pipeline is unstable and blocks delivery." if structured["type"] != "NO_FAILURE" else "No blocker identified."
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
    }.get(structured["type"], "Inspect full logs and resolve root cause.")

    return "\n".join(
        [
            f"Title: [{structured['type']}] {structured['component']} issue",
            f"Type: {structured['type']}",
            f"Component: {structured['component']}",
            f"Severity: {structured['severity']}",
            f"Root Cause: {structured['root_cause']}",
            f"Error: {structured['error']}",
            f"Impact: {impact}",
            f"Proposed Fix: {proposed_fix}",
        ]
    )


def render_jira_markdown(analysis: dict) -> str:
    structured = analysis["structured"]
    lines = [
        f"# Jira Story Draft: {structured['type']} ({structured['component']})",
        "",
        f"- **Type:** {structured['type']}",
        f"- **Component:** {structured['component']}",
        f"- **Severity:** {structured['severity']}",
        f"- **Root Cause:** {structured['root_cause']}",
        f"- **Matches:** {structured['matches']}",
        f"- **Source:** {structured['source']}",
        "",
        "## Mirror Terms",
    ]
    lines.extend([f"- `{term}`" for term in structured["mirror_terms"][:10]])
    lines.extend(
        [
            "",
            "## DSMatrix Ranking",
        ]
    )
    if structured["dsmatrix"]:
        lines.extend([f"- **{row['name']}**: `{row['score']}` ({row['component']})" for row in structured["dsmatrix"]])
    else:
        lines.append("- No rule matches.")
    lines.extend(
        [
            "",
        "## Evidence",
        ]
    )
    if structured["evidence"]:
        lines.extend([f"- L{item['line']} [{item['type']}] {item['text']}" for item in structured["evidence"]])
    else:
        lines.append("- No critical evidence found.")
    lines.extend(["", "## Jira Template", "", render_jira_template(analysis)])
    return "\n".join(lines)


def _emit_json(path: str | None, payload: dict) -> None:
    if not path:
        return
    out = Path(path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def command_logs(args: argparse.Namespace) -> int:
    result = analyze_logs(Path(args.file).expanduser().resolve(), limit=args.limit)
    structured = result["structured"]

    print(f"File: {result['file']}")
    print(f"Total lines: {result['total_lines']}")
    print(f"Critical matches: {result['critical_count']}")
    print(f"Type: {structured['type']}")
    print(f"Component: {structured['component']}")
    print(f"Severity: {structured['severity']}")
    print(f"Root cause: {structured['root_cause']}")

    print("\nGrouped by type:")
    if structured["grouped_by_type"]:
        for failure_type, count in sorted(structured["grouped_by_type"].items(), key=lambda item: item[1], reverse=True):
            print(f"- {failure_type}: {count}")
    else:
        print("- none")

    print("\nEvidence:")
    if structured["evidence"]:
        for entry in structured["evidence"]:
            print(f"[{entry['line']}] ({entry['type']}) {entry['text']}")
    else:
        print("- none")

    if structured["dsmatrix"]:
        print("\nDSMatrix top rules:")
        for row in structured["dsmatrix"]:
            print(f"- {row['name']}: score={row['score']}")

    if args.json:
        print("\nJSON:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    _emit_json(args.json_out, result)
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

            results.append(
                {
                    "path": str(rel_path),
                    "line": index,
                    "score": score,
                    "match": line.strip(),
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


def command_jira_from_log(args: argparse.Namespace) -> int:
    analysis = analyze_logs(Path(args.file).expanduser().resolve(), limit=args.limit)
    ticket = render_jira_template(analysis)
    print(ticket)

    if args.jira_md:
        out = Path(args.jira_md).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_jira_markdown(analysis), encoding="utf-8")

    _emit_json(args.json_out, analysis)
    return 0


def command_jira_story(args: argparse.Namespace) -> int:
    attachments = [Path(path).expanduser().resolve() for path in args.attachment]

    if args.file:
        analysis = analyze_logs(Path(args.file).expanduser().resolve(), limit=args.limit)
    else:
        if not args.context and not attachments:
            raise DeVAIError("Provide --context and/or --attachment when --file is not set")
        analysis = analyze_context(args.context or "", attachments, limit=args.limit)

    ticket = render_jira_template(analysis)
    print(ticket)

    if args.jira_md:
        out = Path(args.jira_md).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_jira_markdown(analysis), encoding="utf-8")

    _emit_json(args.json_out, analysis)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devai",
        description="DevAI Analyther: logs analysis, repository find, and Jira story generation.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    logs_parser = subparsers.add_parser("logs", help="Analyze log file and summarize critical errors")
    logs_parser.add_argument("file", help="Path to log file")
    logs_parser.add_argument("--limit", type=int, default=50, help="Number of latest critical entries to include")
    logs_parser.add_argument("--json", action="store_true", help="Print JSON payload in addition to summary")
    logs_parser.add_argument("--json-out", help="Write structured result to JSON file")
    logs_parser.set_defaults(func=command_logs)

    find_parser = subparsers.add_parser("find", help="Search repository files with simple relevance scoring")
    find_parser.add_argument("query", help="Search query")
    find_parser.add_argument("--root", default=".", help="Repository root path")
    find_parser.add_argument("--limit", type=int, default=25, help="Max number of results")
    find_parser.set_defaults(func=command_find)

    jira_parser = subparsers.add_parser("jira-from-log", help="Generate Jira story draft from a log file")
    jira_parser.add_argument("file", help="Path to log file")
    jira_parser.add_argument("--limit", type=int, default=50, help="Number of latest critical entries to inspect")
    jira_parser.add_argument("--jira-md", help="Write Jira markdown to file (e.g. jira.md)")
    jira_parser.add_argument("--json-out", help="Write structured result to JSON file")
    jira_parser.set_defaults(func=command_jira_from_log)

    story_parser = subparsers.add_parser("jira-story", help="Generate Jira story draft from file/context/attachments")
    story_parser.add_argument("--file", help="Path to log file", default=None)
    story_parser.add_argument("--context", help="Pasted text context", default="")
    story_parser.add_argument("--attachment", action="append", default=[], help="Attached file path (repeatable)")
    story_parser.add_argument("--limit", type=int, default=50, help="Number of critical entries to inspect")
    story_parser.add_argument("--jira-md", help="Write Jira markdown to file (e.g. jira.md)")
    story_parser.add_argument("--json-out", help="Write structured result to JSON file")
    story_parser.set_defaults(func=command_jira_story)

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
