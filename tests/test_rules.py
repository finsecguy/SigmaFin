"""Proves each rule matches its positive samples and not its negative samples.

Rules are converted with the pySigma SQLite backend and run over the sample
events in an in-memory SQLite table. See README for what this does and does not
prove.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import sigmafin_lib as lib  # noqa: E402

DOCS = lib.load_rule_docs()
INDEX = lib.index_docs(DOCS)
PIPELINE_FILES = ("finance_scope.yml",)


def _cases(kind: str):
    cases = []
    for doc in DOCS:
        for sample in lib.sample_files(doc.theme, doc.name, kind):
            cases.append(pytest.param(doc, sample, id=f"{doc.name}/{sample.stem}"))
    return cases


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.name)
def test_rule_has_both_sample_kinds(doc):
    assert lib.sample_files(doc.theme, doc.name, "positive"), "no positive sample"
    assert lib.sample_files(doc.theme, doc.name, "negative"), "no negative sample"


@pytest.mark.parametrize("doc,sample", _cases("positive"))
def test_positive_sample_matches(doc, sample):
    events = lib.load_events(sample)
    pipeline = lib.load_pipeline(*PIPELINE_FILES)
    assert lib.count_matches(doc, INDEX, events, pipeline) >= 1


@pytest.mark.parametrize("doc,sample", _cases("negative"))
def test_negative_sample_does_not_match(doc, sample):
    events = lib.load_events(sample)
    pipeline = lib.load_pipeline(*PIPELINE_FILES)
    assert lib.count_matches(doc, INDEX, events, pipeline) == 0
