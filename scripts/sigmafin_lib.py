"""Shared helpers for the SigmaFin test harness, metadata gate and builders."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from sigma.backends.sqlite import sqliteBackend
from sigma.collection import SigmaCollection
from sigma.processing.pipeline import ProcessingPipeline
from sigma.rule import SigmaRule

ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "rules"
TESTS_DIR = ROOT / "tests"
PIPELINES_DIR = ROOT / "pipelines"
POLICY_FILE = ROOT / "scripts" / "policy.yml"

TIMESTAMP_FIELD = "timestamp"


@dataclass
class RuleDoc:
    """One YAML document from a rule file."""

    path: Path
    theme: str
    data: dict[str, Any]

    @property
    def name(self) -> str:
        return self.data.get("name", "")

    @property
    def id(self) -> str:
        return str(self.data.get("id", ""))

    @property
    def is_correlation(self) -> bool:
        return "correlation" in self.data

    @property
    def references(self) -> list[str]:
        return list(self.data.get("correlation", {}).get("rules", []))


def load_policy(path: Path = POLICY_FILE) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_rule_docs(rules_dir: Path = RULES_DIR) -> list[RuleDoc]:
    docs = []
    for path in sorted(rules_dir.rglob("*.yml")):
        theme = path.relative_to(rules_dir).parts[0]
        for data in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            if data:
                docs.append(RuleDoc(path=path, theme=theme, data=data))
    return docs


def dependencies(doc: RuleDoc, index: dict[str, RuleDoc]) -> list[RuleDoc]:
    """Return all rule documents a correlation needs, transitively."""
    found: dict[str, RuleDoc] = {}
    stack = list(doc.references)
    while stack:
        ref = stack.pop()
        dep = index.get(ref)
        if dep is None:
            raise KeyError(f"{doc.name}: unresolved correlation reference {ref!r}")
        if dep.name not in found:
            found[dep.name] = dep
            stack.extend(dep.references)
    return list(found.values())


def index_docs(docs: list[RuleDoc]) -> dict[str, RuleDoc]:
    index: dict[str, RuleDoc] = {}
    for doc in docs:
        index[doc.name] = doc
        index[doc.id] = doc
    return index


def build_collection(doc: RuleDoc, index: dict[str, RuleDoc]) -> SigmaCollection:
    deps = dependencies(doc, index) if doc.is_correlation else []
    return SigmaCollection.from_dicts([d.data for d in deps] + [doc.data])


def load_pipeline(*names: str) -> ProcessingPipeline:
    pipeline = ProcessingPipeline()
    for name in names:
        pipeline = pipeline + ProcessingPipeline.from_yaml(
            (PIPELINES_DIR / name).read_text(encoding="utf-8")
        )
    return pipeline


# ---------------------------------------------------------------------------
# Field discovery
# ---------------------------------------------------------------------------

def _detection_fields(detection) -> set[str]:
    fields: set[str] = set()
    for item in detection.detection_items:
        if hasattr(item, "detection_items"):
            fields |= _detection_fields(item)
        elif item.field:
            fields.add(item.field)
    return fields


def rule_fields(doc: RuleDoc, index: dict[str, RuleDoc]) -> set[str]:
    """Every field a rule (and the rules it depends on) reads."""
    fields: set[str] = {TIMESTAMP_FIELD}
    targets = [doc] + (dependencies(doc, index) if doc.is_correlation else [])
    for target in targets:
        if target.is_correlation:
            corr = target.data["correlation"]
            fields |= set(corr.get("group-by", []))
            cond = corr.get("condition") or {}
            if isinstance(cond, dict) and cond.get("field"):
                fields.add(cond["field"])
        else:
            rule = SigmaRule.from_dict(target.data)
            for detection in rule.detection.detections.values():
                fields |= _detection_fields(detection)
    return fields


# ---------------------------------------------------------------------------
# SQLite evaluation
# ---------------------------------------------------------------------------

class SampleError(Exception):
    """A sample or rule is unusable. Never treated as 'no match'."""


def load_events(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    events = data if isinstance(data, list) else [data]
    if not events:
        raise SampleError(f"{path}: empty sample")
    for event in events:
        if not isinstance(event, dict):
            raise SampleError(f"{path}: events must be JSON objects")
        if TIMESTAMP_FIELD not in event:
            raise SampleError(f"{path}: event without a {TIMESTAMP_FIELD!r} field")
    return events


def _sql_value(value: Any) -> Any:
    # Sigma compares booleans against the strings 'true' and 'false'.
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        raise SampleError("samples must be flat: nested objects and lists are not supported")
    return value


def build_database(events: list[dict[str, Any]], fields: set[str]) -> sqlite3.Connection:
    columns = sorted({k for e in events for k in e} | fields)
    conn = sqlite3.connect(":memory:")
    ddl = ", ".join(f'"{c}" TEXT COLLATE NOCASE' for c in columns)
    conn.execute(f"CREATE TABLE logs ({ddl})")
    quoted = ", ".join(f'"{c}"' for c in columns)
    marks = ", ".join("?" for _ in columns)
    for event in events:
        conn.execute(
            f"INSERT INTO logs ({quoted}) VALUES ({marks})",
            [_sql_value(event.get(c)) for c in columns],
        )
    bad = conn.execute(
        f'SELECT COUNT(*) FROM logs WHERE julianday("{TIMESTAMP_FIELD}") IS NULL'
    ).fetchone()[0]
    if bad:
        raise SampleError(
            f"{bad} event(s) have a {TIMESTAMP_FIELD!r} SQLite cannot parse "
            "(use ISO 8601, for example 2026-03-02T09:15:00Z)"
        )
    return conn


def convert_to_sql(doc: RuleDoc, index: dict[str, RuleDoc], pipeline: ProcessingPipeline) -> str:
    backend = sqliteBackend(processing_pipeline=pipeline)
    queries = backend.convert(build_collection(doc, index))
    if len(queries) != 1 or not isinstance(queries[0], str):
        raise SampleError(f"{doc.name}: expected exactly one SQL query, got {len(queries)}")
    return queries[0]


def count_matches(
    doc: RuleDoc,
    index: dict[str, RuleDoc],
    events: list[dict[str, Any]],
    pipeline: ProcessingPipeline,
) -> int:
    """Run the converted rule over events. Any SQL error propagates as a failure."""
    sql = convert_to_sql(doc, index, pipeline)
    conn = build_database(events, rule_fields(doc, index))
    try:
        return len(conn.execute(sql).fetchall())
    finally:
        conn.close()


def sample_files(theme: str, name: str, kind: str, tests_dir: Path = TESTS_DIR) -> list[Path]:
    return sorted((tests_dir / theme / name / kind).glob("*.json"))


UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
