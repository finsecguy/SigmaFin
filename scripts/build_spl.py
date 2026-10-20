"""Convert every SigmaFin rule to Splunk SPL.

Writes build/spl/<theme>/<rule_name>.spl and build/spl/SUMMARY.md.

Conversion is strict. A rule that fails to convert fails the build unless it is
listed under splunk_unsupported in scripts/policy.yml, and a listed rule that
now converts also fails the build so the list cannot go stale. Support rules
(policy support_rules) are converted only as part of their correlation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sigma.backends.splunk import SplunkBackend
from sigma.exceptions import SigmaError

import sigmafin_lib as lib

PIPELINES = ("finance_scope.yml", "sigmafin_splunk.yml")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=lib.ROOT / "build" / "spl")
    parser.add_argument("--policy", type=Path, default=lib.POLICY_FILE)
    args = parser.parse_args(argv)

    policy = lib.load_policy(args.policy)
    unsupported = {e["name"]: e["reason"] for e in policy.get("splunk_unsupported", [])}
    support = set(policy.get("support_rules", []))
    docs = lib.load_rule_docs()
    index = lib.index_docs(docs)

    failures: list[str] = []
    rows: list[tuple[str, str, str]] = []
    for doc in docs:
        if doc.name in support:
            rows.append((doc.name, "support rule", "converted only inside its correlation"))
            continue
        backend = SplunkBackend(processing_pipeline=lib.load_pipeline(*PIPELINES))
        try:
            queries = backend.convert(lib.build_collection(doc, index))
        except (SigmaError, NotImplementedError) as exc:
            if doc.name in unsupported:
                rows.append((doc.name, "unsupported", unsupported[doc.name]))
            else:
                failures.append(f"{doc.name}: conversion failed and is not listed in policy.yml: {exc}")
            continue
        if doc.name in unsupported:
            failures.append(f"{doc.name}: listed as splunk_unsupported but it converts; remove it from policy.yml")
            continue
        target = args.out / doc.theme / f"{doc.name}.spl"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n\n".join(str(q) for q in queries) + "\n", encoding="utf-8")
        rows.append((doc.name, "converted", str(target.relative_to(args.out))))

    args.out.mkdir(parents=True, exist_ok=True)
    lines = ["# Splunk conversion summary", "", "| Rule | Result | Detail |", "|---|---|---|"]
    lines += [f"| {n} | {r} | {d} |" for n, r, d in rows]
    (args.out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for row in rows:
        print(" | ".join(row))
    for f in failures:
        print(f"ERROR {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
