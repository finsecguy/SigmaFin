"""The vendor bank change rule, converted with pipelines/sap_erp.yml.

Positive fixtures are change-document shaped rows that should match. Negative
fixtures are near misses, including an IBAN row the pipeline deliberately does
not map (docs/sap-mapping.md).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_sap_pipeline  # noqa: E402
import sigmafin_lib as lib  # noqa: E402

FIXTURES = ROOT / "tests" / "sap_pipeline"


def test_bank_rule_converts_to_sap_predicates():
    assert check_sap_pipeline.main() == 0


@pytest.mark.parametrize("path", sorted((FIXTURES / "positive").glob("*.json")), ids=lambda p: p.stem)
def test_sap_fixture_matches(path):
    docs = lib.load_rule_docs()
    index = lib.index_docs(docs)
    doc = index[check_sap_pipeline.RULE]
    pipeline = lib.load_pipeline("finance_scope.yml", "sap_erp.yml")
    assert lib.count_matches(doc, index, lib.load_events(path), pipeline) >= 1


@pytest.mark.parametrize("path", sorted((FIXTURES / "negative").glob("*.json")), ids=lambda p: p.stem)
def test_sap_fixture_does_not_match(path):
    docs = lib.load_rule_docs()
    index = lib.index_docs(docs)
    doc = index[check_sap_pipeline.RULE]
    pipeline = lib.load_pipeline("finance_scope.yml", "sap_erp.yml")
    assert lib.count_matches(doc, index, lib.load_events(path), pipeline) == 0
