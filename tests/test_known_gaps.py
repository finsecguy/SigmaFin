"""Asserts documented detection gaps. See tests/known_gaps/README.md."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import sigmafin_lib as lib  # noqa: E402

DOCS = lib.load_rule_docs()
INDEX = lib.index_docs(DOCS)
GAPS = sorted((lib.TESTS_DIR / "known_gaps").glob("*/*.json"))


def test_known_gaps_exist():
    assert GAPS


@pytest.mark.parametrize("sample", GAPS, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_known_gap_is_still_a_miss(sample):
    doc = INDEX[sample.parent.name]
    events = lib.load_events(sample)
    pipeline = lib.load_pipeline("finance_scope.yml")
    assert lib.count_matches(doc, INDEX, events, pipeline) == 0, (
        "the rule now matches this sample: the gap is fixed, move it to positive/ and update the docs"
    )
