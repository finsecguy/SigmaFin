"""Every correlation the backends cannot convert has a hand-written query."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sigmafin_lib as lib  # noqa: E402

HAND = ROOT / "docs" / "handwritten"


def _required() -> dict[str, list[str]]:
    policy = lib.load_policy()
    splunk = {entry["name"] for entry in policy["splunk_unsupported"]}
    kusto = {entry["name"] for entry in policy["kusto_unsupported"]}
    required = {}
    for name in sorted(splunk | kusto):
        exts = []
        if name in splunk:
            exts.append("spl")
        if name in kusto:
            exts.append("kql")
        required[name] = exts
    return required


def test_each_unsupported_rule_has_a_handwritten_file():
    docs = lib.load_rule_docs()
    index = lib.index_docs(docs)
    for name, exts in _required().items():
        doc = index[name]
        timespan = doc.data["correlation"]["timespan"]
        for ext in exts:
            path = HAND / f"{name}.{ext}"
            assert path.is_file(), f"missing {path}"
            text = path.read_text(encoding="utf-8")
            assert "hand-written" in text
            assert "not generated" in text
            assert doc.id in text
            assert timespan in text
            for field in doc.data["correlation"]["group-by"]:
                assert field in text, f"{path.name} missing group-by field {field}"


def test_entra_handwritten_lists_finance_users():
    scope = (ROOT / "pipelines" / "finance_scope.yml").read_text(encoding="utf-8")
    # The synthetic list is the finance_users block. Read it the same way the pipeline does.
    import yaml

    users = yaml.safe_load(scope)["vars"]["finance_users"]
    assert users, "finance_users is empty"
    for ext in ("spl", "kql"):
        text = (HAND / f"entra_anonymous_signin_then_inbox_rule.{ext}").read_text(encoding="utf-8")
        for user in users:
            assert user in text, f"{ext} is missing finance user {user}"
