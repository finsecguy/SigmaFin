# Known gap: m365_inbox_rule_hides_finance_mail

Samples here are events the rule *should* flag but currently misses. `tests/test_known_gaps.py` asserts the miss, so
the gap stays visible. If the rule is fixed, the test fails: move the sample to `positive/` and update the docs.

- `sender_domain_rule_without_keywords.json`: a rule that moves all mail from one sender to Archive and marks it as
  read, with no subject or body keywords. The rule requires a finance keyword, so it is missed.
