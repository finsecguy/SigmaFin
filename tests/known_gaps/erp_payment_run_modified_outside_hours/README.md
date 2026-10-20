# Known gap: erp_payment_run_modified_outside_hours

Samples here are events the rule *should* flag but currently misses. `tests/test_known_gaps.py` asserts the miss, so
the gap stays visible. If the rule is fixed, the test fails: move the sample to `positive/` and update the docs.

- `run_modified_at_night_enrichment_field_missing.json`: a payment run modified in the middle of the night, but the
  `outside_business_hours` field is absent because ingestion did not enrich the event. The rule reads only that field,
  so it fails open: it does not match, and nothing says the rule is blind. This is a silent failure, not intended
  behaviour. Monitor how many payments events carry the field.
