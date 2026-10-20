# Known gaps

Samples here are events the rule *should* flag but currently misses. `tests/test_known_gaps.py` asserts the miss, so
the gap stays visible. If a rule is fixed, the test fails: move the sample to `positive/` and delete the gap test.

- `external_recipient_followed_by_internal.json`: one field holds several recipients and the last one is internal.
  The rule only judges the end of the value, so the external first recipient is missed.
