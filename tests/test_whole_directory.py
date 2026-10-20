"""Converting the whole rules/ directory in one run must keep every alerting rule."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sigma.backends.sqlite import sqliteBackend  # noqa: E402
from sigma.collection import SigmaCollection  # noqa: E402

import sigmafin_lib as lib  # noqa: E402

DOCS = lib.load_rule_docs()
INDEX = lib.index_docs(DOCS)
SUPPORT = set(lib.load_policy().get("support_rules", []))


def _convert_all() -> list[str]:
    backend = sqliteBackend(processing_pipeline=lib.load_pipeline("finance_scope.yml"))
    return backend.convert(SigmaCollection.from_dicts([d.data for d in DOCS]))


def test_whole_directory_outputs_every_non_support_rule():
    queries = _convert_all()
    assert len(queries) == len([d for d in DOCS if d.name not in SUPPORT])


def test_standalone_bank_rule_still_converts_and_alerts_in_a_whole_run():
    doc = INDEX["erp_vendor_bank_details_changed"]
    pipeline = lib.load_pipeline("finance_scope.yml")
    standalone = lib.convert_to_sql(doc, INDEX, pipeline)
    assert standalone in _convert_all()
    sample = lib.sample_files(doc.theme, doc.name, "positive")[0]
    assert lib.count_matches(doc, INDEX, lib.load_events(sample), pipeline) >= 1

