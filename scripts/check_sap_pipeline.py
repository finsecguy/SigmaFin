"""Fail unless the vendor bank change rule converts through pipelines/sap_erp.yml.

The Splunk and SQLite queries must carry the SAP predicates and must not still
mention the SigmaFin bank-field vocabulary. Fixture matching lives in
tests/test_sap_pipeline.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sigma.backends.splunk import SplunkBackend
from sigma.backends.sqlite import sqliteBackend

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sigmafin_lib as lib  # noqa: E402

RULE = "erp_vendor_bank_details_changed"
# Values the pipeline must emit. IBAN, SWIFT and bank name are intentionally
# absent: they are not LFBK columns. See docs/sap-mapping.md.
REQUIRED = (
    "OBJECTCLAS",
    "KRED",
    "TABNAME",
    "LFBK",
    "CHANGE_IND",
    "FNAME",
    "BANKN",
    "BANKL",
    "BANKS",
    "FK02",
    "XK02",
    "MK02",
    "BP",
)
ABSENT = (
    "bank_account_number",
    "bank_routing_number",
    "bank_country",
    "swift_bic",
    "bank_name",
    "field_changed",
    "vendor_updated",
    "success",
)


def convert(backend_name: str) -> str:
    docs = lib.load_rule_docs()
    index = lib.index_docs(docs)
    doc = index[RULE]
    pipeline = lib.load_pipeline("finance_scope.yml", "sap_erp.yml")
    backend_cls = {"sqlite": sqliteBackend, "splunk": SplunkBackend}[backend_name]
    queries = backend_cls(processing_pipeline=pipeline).convert(lib.build_collection(doc, index))
    if len(queries) != 1:
        raise RuntimeError(f"{backend_name}: expected one query, got {len(queries)}")
    return str(queries[0])


def check(query: str, backend_name: str) -> list[str]:
    errors = []
    for token in REQUIRED:
        if token not in query:
            errors.append(f"{backend_name}: missing {token}")
    for token in ABSENT:
        if token in query:
            errors.append(f"{backend_name}: still contains {token}")
    return errors


# Other ERP rules the same pipeline rewrites. Tokens that must appear, then
# tokens that must not. The bank rule is checked more strictly above.
OTHERS = {
    "erp_new_vendor_created_event": (("KRED", "LFA1", "LFB1", "FK01", "XK01"), ("vendor_created", "success")),
    "erp_vendor_payment_released": (("F110", "XVORL"), ("payment_released", "success")),
    "erp_privileged_role_assigned_without_approval": (
        ("PFCG", "AGR_USERS", "SU01", "AGR_NAME", "approval_status"),
        ("role_assigned", "success"),
    ),
    "erp_emergency_access_started": (("emergency_access_started",), ("success",)),
    "erp_payment_run_modified_outside_hours": (("payment_run_modified", "outside_business_hours"), ("success",)),
    "erp_sod_payment_approved_event": (("payment_approved",), ("success",)),
}


def check_others() -> list[str]:
    docs = lib.load_rule_docs()
    index = lib.index_docs(docs)
    pipeline = lib.load_pipeline("finance_scope.yml", "sap_erp.yml")
    errors = []
    for name, (required, absent) in OTHERS.items():
        doc = index[name]
        query = str(SplunkBackend(processing_pipeline=pipeline).convert(lib.build_collection(doc, index))[0])
        print(f"{name}: {query}")
        for token in required:
            if token not in query:
                errors.append(f"{name}: missing {token}")
        for token in absent:
            if token in query:
                errors.append(f"{name}: still contains {token}")
    return errors


def main(argv: list[str] | None = None) -> int:
    del argv
    errors: list[str] = []
    for backend_name in ("sqlite", "splunk"):
        try:
            query = convert(backend_name)
        except Exception as exc:  # conversion failure is the gate
            errors.append(f"{backend_name}: conversion failed: {exc}")
            continue
        print(f"{backend_name}: {query}")
        errors.extend(check(query, backend_name))
    try:
        errors.extend(check_others())
    except Exception as exc:
        errors.append(f"other ERP rules: conversion failed: {exc}")
    for error in errors:
        print(f"ERROR {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
