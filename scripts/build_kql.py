"""Convert every SigmaFin rule to Kusto Query Language (KQL).

Writes build/kql/<theme>/<rule_name>.kql and build/kql/SUMMARY.md.

Conversion is strict. A rule that fails to convert fails the build unless it is
listed under kusto_unsupported in scripts/policy.yml, and a listed rule that
now converts also fails the build so the list cannot go stale. Support rules
(policy support_rules) are converted only as part of their correlation.

The output is the same shape as scripts/build_spl.py. Table names come from
pipelines/sigmafin_kusto.yml. The shipped names are Microsoft Sentinel tables
where the rule fields already match (OfficeActivity, SigninLogs) and
placeholder names for the ERP schema. Defender XDR advanced hunting needs its
own table and field mapping in that pipeline.

The Kusto backend quotes dotted field names with single quotes. In KQL a
single-quoted token is a string, so Parameters.ForwardTo would never match
the column. This script rewrites those identifiers to KQL bracket quotes.
String values stay double-quoted, which is how the backend emits them.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from sigma.backends.kusto import KustoBackend
from sigma.exceptions import SigmaError

import sigmafin_lib as lib

PIPELINES = ("finance_scope.yml", "sigmafin_kusto.yml")
TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\n\| where ")
FIELD_QUOTE_RE = re.compile(r"'([A-Za-z_][\w.]*)'")


def kql_identifier_quotes(query: str) -> str:
    """Turn backend single-quoted field names into KQL bracket identifiers."""
    return FIELD_QUOTE_RE.sub(r"['\1']", query)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=lib.ROOT / "build" / "kql")
    parser.add_argument("--policy", type=Path, default=lib.POLICY_FILE)
    args = parser.parse_args(argv)

    policy = lib.load_policy(args.policy)
    unsupported = {e["name"]: e["reason"] for e in policy.get("kusto_unsupported", [])}
    support = set(policy.get("support_rules", []))
    docs = lib.load_rule_docs()
    index = lib.index_docs(docs)

    failures: list[str] = []
    rows: list[tuple[str, str, str]] = []
    for doc in docs:
        if doc.name in support:
            rows.append((doc.name, "support rule", "converted only inside its correlation"))
            continue
        backend = KustoBackend(processing_pipeline=lib.load_pipeline(*PIPELINES))
        try:
            queries = [kql_identifier_quotes(str(q)) for q in backend.convert(lib.build_collection(doc, index))]
        except (SigmaError, NotImplementedError) as exc:
            if doc.name in unsupported:
                rows.append((doc.name, "unsupported", unsupported[doc.name]))
            else:
                failures.append(f"{doc.name}: conversion failed and is not listed in policy.yml: {exc}")
            continue
        if doc.name in unsupported:
            failures.append(f"{doc.name}: listed as kusto_unsupported but it converts; remove it from policy.yml")
            continue
        missing = [q for q in queries if not TABLE_RE.match(q)]
        if missing:
            failures.append(
                f"{doc.name}: KQL has no table name; add its logsource to pipelines/sigmafin_kusto.yml"
            )
            continue
        target = args.out / doc.theme / f"{doc.name}.kql"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n\n".join(queries) + "\n", encoding="utf-8")
        rows.append((doc.name, "converted", str(target.relative_to(args.out))))

    args.out.mkdir(parents=True, exist_ok=True)
    lines = ["# KQL conversion summary", "", "| Rule | Result | Detail |", "|---|---|---|"]
    lines += [f"| {n} | {r} | {d} |" for n, r, d in rows]
    (args.out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for row in rows:
        print(" | ".join(row))
    for failure in failures:
        print(f"ERROR {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
