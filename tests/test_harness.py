"""Unit tests for the harness itself: it must be able to fail.

Without these, a harness bug (for example a SQL error or empty table treated as
'no match') would let every negative sample pass without testing anything.
"""

from __future__ import annotations

import copy
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import sigmafin_lib as lib  # noqa: E402

DOCS = lib.load_rule_docs()
INDEX = lib.index_docs(DOCS)
PIPELINE = lib.load_pipeline("finance_scope.yml")

BANK = INDEX["erp_vendor_bank_details_changed"]
CORR = INDEX["erp_vendor_bank_change_then_payment"]
FWD = INDEX["m365_inbox_rule_external_forward_finance"]


def _events(theme, rule, kind, stem):
    return lib.load_events(lib.TESTS_DIR / theme / rule / kind / f"{stem}.json")


def test_positive_event_used_as_negative_is_caught():
    events = _events("erp_vendor_payment", BANK.name, "positive", "account_number_changed")
    assert lib.count_matches(BANK, INDEX, events, PIPELINE) >= 1


def test_broken_rule_fails_its_positive_sample():
    broken = lib.RuleDoc(BANK.path, BANK.theme, copy.deepcopy(BANK.data))
    broken.data["detection"]["selection"]["action"] = "vendor_deleted"
    events = _events("erp_vendor_payment", BANK.name, "positive", "account_number_changed")
    assert lib.count_matches(broken, INDEX, events, PIPELINE) == 0


def test_null_timestamp_is_an_error_not_a_non_match():
    with pytest.raises(lib.SampleError):
        lib.build_database([{"timestamp": "not a time", "action": "x"}], {"action"})


def test_missing_timestamp_is_an_error():
    path = lib.ROOT / "scripts" / "_tmp_no_ts.json"
    path.write_text('{"action": "x"}', encoding="utf-8")
    try:
        with pytest.raises(lib.SampleError):
            lib.load_events(path)
    finally:
        path.unlink()


def test_sample_without_rule_field_is_a_non_match_not_an_error():
    # Field absent from every event: column is created as NULL so the rule
    # simply does not match, and the same sample cannot hide a SQL error.
    events = [{"timestamp": "2026-03-02T09:00:00Z", "Operation": "New-InboxRule",
               "UserId": "ap@finance.example.com"}]
    assert lib.count_matches(FWD, INDEX, events, PIPELINE) == 0


def test_sql_error_propagates():
    conn = lib.build_database([{"timestamp": "2026-03-02T09:00:00Z"}], set())
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("SELECT * FROM logs WHERE no_such_column = 'x'")


def test_nested_sample_values_are_rejected():
    with pytest.raises(lib.SampleError):
        lib.build_database([{"timestamp": "2026-03-02T09:00:00Z", "a": {"b": 1}}], set())


def _bank(ts, vendor="V1", field="iban"):
    return {"timestamp": ts, "action": "vendor_updated", "status": "success",
            "vendor_id": vendor, "field_changed": field}


def _pay(ts, vendor="V1"):
    return {"timestamp": ts, "action": "payment_released", "status": "success", "vendor_id": vendor}


@pytest.mark.parametrize(
    "events,expected",
    [
        ([_bank("2026-03-02T09:00:00Z"), _pay("2026-03-02T09:00:01Z")], 1),
        ([_pay("2026-03-02T08:59:59Z"), _bank("2026-03-02T09:00:00Z")], 0),
        ([_bank("2026-03-02T09:00:00Z"), _pay("2026-03-05T08:59:59Z")], 1),
        ([_bank("2026-03-02T09:00:00Z"), _pay("2026-03-05T09:00:01Z")], 0),
        ([_bank("2026-03-02T09:00:00Z"), _pay("2026-03-03T09:00:00Z", vendor="V2")], 0),
        ([_bank("2026-03-02T09:00:00Z", vendor="V2"), _pay("2026-03-03T09:00:00Z", vendor="V1")], 0),
    ],
    ids=["after", "before", "inside_window_edge", "outside_window_edge", "other_vendor", "vendors_swapped"],
)
def test_temporal_ordered_semantics(events, expected):
    assert (lib.count_matches(CORR, INDEX, events, PIPELINE) >= 1) == bool(expected)
