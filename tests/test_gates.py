"""Proves each CI gate fails on a deliberately broken input.

A gate that has never been seen to fail proves nothing, so each case here
copies the real rules into a temp directory, breaks one thing, and asserts the
gate exits non-zero. The unbroken copy must pass.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_spl  # noqa: E402
import check_metadata  # noqa: E402
import check_no_em_dash  # noqa: E402
import sigmafin_lib as lib  # noqa: E402

BANK = "erp_vendor_payment/erp_vendor_bank_details_changed.yml"


@pytest.fixture()
def tree(tmp_path):
    shutil.copytree(lib.RULES_DIR, tmp_path / "rules")
    shutil.copytree(lib.TESTS_DIR, tmp_path / "tests", ignore=shutil.ignore_patterns("__pycache__", "*.py"))
    return tmp_path


def _meta(tree):
    return check_metadata.main(["--rules", str(tree / "rules"), "--tests", str(tree / "tests")])


def _sigma_check(rules: Path) -> int:
    exe = Path(sys.executable).parent / "sigma"
    cmd = [str(exe) if exe.exists() else "sigma", "check", "-i", "-e", str(rules)]
    return subprocess.run(cmd, capture_output=True, text=True).returncode


def _edit(path: Path, old: str, new: str):
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_unbroken_tree_passes_every_gate(tree):
    assert _meta(tree) == 0
    assert _sigma_check(tree / "rules") == 0


def test_sigma_check_fails_on_unknown_attack_technique(tree):
    _edit(tree / "rules" / BANK, "attack.t1657", "attack.t9999")
    assert _sigma_check(tree / "rules") != 0


def test_sigma_check_fails_on_unknown_attack_tactic(tree):
    _edit(tree / "rules" / BANK, "attack.impact", "attack.not-a-tactic")
    assert _sigma_check(tree / "rules") != 0


def test_metadata_gate_fails_on_missing_references(tree):
    path = tree / "rules" / BANK
    text = path.read_text(encoding="utf-8")
    start = text.index("references:")
    end = text.index("author:")
    path.write_text(text[:start] + text[end:], encoding="utf-8")
    assert _meta(tree) != 0


def test_metadata_gate_fails_on_missing_technique_tag(tree):
    _edit(tree / "rules" / BANK, "    - attack.t1657\n", "")
    assert _meta(tree) != 0


def test_metadata_gate_fails_on_missing_negative_sample(tree):
    shutil.rmtree(tree / "tests" / "erp_vendor_payment" / "erp_vendor_bank_details_changed" / "negative")
    assert _meta(tree) != 0


def test_metadata_gate_fails_on_duplicate_id(tree):
    other = tree / "rules" / "bec_payment_fraud" / "m365_inbox_rule_external_forward_finance.yml"
    _edit(other, "4b0f8f5e-2c6a-4d1e-9a47-3e5d7b1c9f20", "9c3a1e7d-5f42-4b8a-8d16-0a7e2b4c6d51")
    assert _meta(tree) != 0


def test_spl_build_fails_when_unsupported_rule_is_not_listed(tree, tmp_path):
    empty = tmp_path / "policy.yml"
    empty.write_text("no_technique: []\nsupport_rules: [erp_vendor_payment_released]\nsplunk_unsupported: []\n")
    assert build_spl.main(["--out", str(tmp_path / "out"), "--policy", str(empty)]) != 0


def test_spl_build_fails_when_listed_rule_actually_converts(tmp_path):
    policy = tmp_path / "policy.yml"
    policy.write_text(
        "no_technique: []\nsupport_rules: [erp_vendor_payment_released]\n"
        "splunk_unsupported:\n"
        "  - {name: erp_vendor_bank_change_then_payment, reason: x}\n"
        "  - {name: erp_vendor_bank_details_changed, reason: stale entry}\n"
    )
    assert build_spl.main(["--out", str(tmp_path / "out"), "--policy", str(policy)]) != 0


def test_em_dash_gate_fails_on_em_dash(tmp_path):
    bad = tmp_path / "doc.md"
    bad.write_text("text " + chr(0x2014) + " text\n", encoding="utf-8")
    ok = tmp_path / "ok.md"
    ok.write_text("plain text\n", encoding="utf-8")
    assert check_no_em_dash.scan([str(ok)]) == 0
    assert check_no_em_dash.scan([str(bad)]) != 0
