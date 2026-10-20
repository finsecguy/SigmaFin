"""Metadata gate for CI.

Fails on: missing or malformed id/name/title/description/author/date/level,
missing falsepositives, missing references, missing ATT&CK technique tag
(unless the rule is listed in scripts/policy.yml), duplicate ids or names,
unresolved correlation references, and rules without positive and negative
samples. Tag validity (known technique and tactic names) is checked by
`sigma check`, not here.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import sigmafin_lib as lib

REQUIRED = ("title", "id", "name", "status", "description", "author", "date", "level", "falsepositives")
STATUSES = {"stable", "test", "experimental", "deprecated", "unsupported"}
LEVELS = {"informational", "low", "medium", "high", "critical"}
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def check(rules_dir: Path, tests_dir: Path, policy_file: Path) -> list[str]:
    errors: list[str] = []
    policy = lib.load_policy(policy_file)
    no_technique = {e["name"] for e in policy.get("no_technique", [])}
    docs = lib.load_rule_docs(rules_dir)
    index = lib.index_docs(docs)

    seen_ids: dict[str, str] = {}
    seen_names: dict[str, str] = {}
    for doc in docs:
        d = doc.data
        where = f"{doc.path.name}:{doc.name or doc.id or '?'}"
        for key in REQUIRED:
            if not d.get(key):
                errors.append(f"{where}: missing {key}")
        if d.get("id") and not lib.UUID_RE.match(str(d["id"])):
            errors.append(f"{where}: id is not a lowercase UUID")
        if d.get("name") and not NAME_RE.match(d["name"]):
            errors.append(f"{where}: name must be snake_case")
        if d.get("status") and d["status"] not in STATUSES:
            errors.append(f"{where}: invalid status {d['status']!r}")
        if d.get("level") and d["level"] not in LEVELS:
            errors.append(f"{where}: invalid level {d['level']!r}")
        if d.get("date") and not DATE_RE.match(str(d["date"])):
            errors.append(f"{where}: date must be YYYY-MM-DD")
        refs = d.get("references") or []
        if not refs:
            errors.append(f"{where}: missing references")
        for ref in refs:
            if not str(ref).startswith("https://"):
                errors.append(f"{where}: reference is not an https URL: {ref}")
        if not doc.is_correlation and not d.get("logsource"):
            errors.append(f"{where}: missing logsource")
        if d.get("id") in seen_ids:
            errors.append(f"{where}: duplicate id, also used by {seen_ids[d['id']]}")
        if d.get("name") in seen_names:
            errors.append(f"{where}: duplicate name, also used by {seen_names[d['name']]}")
        seen_ids[d.get("id")] = where
        seen_names[d.get("name")] = where

        tags = d.get("tags") or []
        techniques = [t for t in tags if re.match(r"^attack\.t\d{4}(\.\d{3})?$", t)]
        if doc.name in no_technique:
            if "no att&ck" not in (d.get("description") or "").lower():
                errors.append(f"{where}: allowed without technique but description lacks a 'No ATT&CK' explanation")
            if techniques:
                errors.append(f"{where}: listed in no_technique but has a technique tag")
        elif not techniques:
            errors.append(f"{where}: missing attack.tNNNN tag (add one or list the rule in policy.yml with a reason)")
        if techniques and not any(re.match(r"^attack\.[a-z][a-z-]+$", t) for t in tags):
            errors.append(f"{where}: has a technique tag but no attack.<tactic> tag")

        if doc.is_correlation:
            for ref in doc.references:
                if ref not in index:
                    errors.append(f"{where}: unresolved correlation reference {ref!r}")

        for kind in ("positive", "negative"):
            if not lib.sample_files(doc.theme, doc.name, kind, tests_dir):
                errors.append(f"{where}: no {kind} sample in tests/{doc.theme}/{doc.name}/{kind}/")

    for entry in policy.get("no_technique", []) + policy.get("support_rules", []) + policy.get("splunk_unsupported", []):
        name = entry["name"] if isinstance(entry, dict) else entry
        if name not in index:
            errors.append(f"policy.yml lists unknown rule {name!r}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules", type=Path, default=lib.RULES_DIR)
    parser.add_argument("--tests", type=Path, default=lib.TESTS_DIR)
    parser.add_argument("--policy", type=Path, default=lib.POLICY_FILE)
    args = parser.parse_args(argv)
    errors = check(args.rules, args.tests, args.policy)
    for e in errors:
        print(f"ERROR {e}")
    print(f"{len(errors)} metadata error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
