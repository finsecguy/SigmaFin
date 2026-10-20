# SigmaFin

SigmaFin is a collection of Sigma detection rules for threats against corporate finance departments: accounts
payable, treasury, payroll, financial reporting and the ERP systems behind them. It is for detection engineers and
SOC analysts who need finance-specific coverage on top of generic rule sets, and it is a portfolio project, so
testing and documentation come before rule count.

**Status: work in progress.** 3 of the planned 25 rules exist. The table below lists only what is built.

## Rules

<!-- RULES:START -->
| Rule | Theme | ATT&CK technique | Log source | Level |
|---|---|---|---|---|
| Finance Mailbox Inbox Rule Forwards Mail to External Address (`m365_inbox_rule_external_forward_finance`) | 1. BEC and payment fraud | T1114.003 Email Forwarding Rule | m365/audit | high |
| Vendor Bank Details Changed Then Payment Released (`erp_vendor_bank_change_then_payment`) | 2. Vendor and payment manipulation (ERP) | T1657 Financial Theft | erp/vendor_master + erp/payments | high |
| Vendor Master Bank Details Changed (`erp_vendor_bank_details_changed`) | 2. Vendor and payment manipulation (ERP) | T1657 Financial Theft | erp/vendor_master | medium |
| Vendor Payment Released (`erp_vendor_payment_released`) | 2. Vendor and payment manipulation (ERP) | none (fraud or support rule) | erp/payments | informational |
<!-- RULES:END -->

Per-rule SigmaHQ overlap decisions are in [docs/rule-catalog.md](docs/rule-catalog.md). The ATT&CK table is in
[docs/attack-coverage.md](docs/attack-coverage.md). Both are generated.

## Finance processes protected

| Process | Themes | What goes wrong |
|---|---|---|
| Accounts payable | BEC and payment fraud, vendor and payment manipulation | Mailbox takeover, redirected vendor bank details, fake or fast-paid vendors, split duties broken |
| Treasury | Vendor and payment manipulation, account takeover | Payment run tampering, takeover of approvers' accounts |
| Payroll | BEC, exfiltration and insider risk | Forwarded payroll mail, bulk payroll downloads |
| Financial reporting | Privileged ERP abuse, exfiltration, AI leakage | Direct table edits, early access to results, pasting results into public AI chat |

Only the first two themes have rules so far.

## Setup

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

Versions are pinned. sigma-cli 3.1.0 requires pySigma below 2.0, so the set is pySigma 1.5.1 with the SQLite backend
2.0.0 and the Splunk backend 2.1.0. Newer backend releases need pySigma 2.x and cannot be installed alongside
sigma-cli 3.1.0 yet.

## Run locally

```bash
sigma check --fail-on-issues --fail-on-error rules      # Sigma validation
python scripts/check_metadata.py                        # references, ATT&CK tags, ids, samples
python -m pytest -q tests                               # samples, harness self-tests, gate self-tests
python scripts/build_spl.py                             # Splunk SPL into build/spl/
python scripts/gen_docs.py                              # regenerate README table, catalog, ATT&CK table
python scripts/check_no_em_dash.py
```

CI runs the same steps on every push and publishes `build/spl` as the `splunk-spl` artifact.

## How the tests work

`pytest` converts each rule with the pySigma SQLite backend, loads each sample event into an in-memory SQLite table,
and runs the query. Positive samples must match and negative samples must not. Correlation rules are converted by the
same backend, which supports `event_count`, `value_count`, `temporal` and `temporal_ordered`, so no custom evaluator
is used. Details that keep a negative from passing by accident: a SQL error or an unparseable timestamp fails the
test instead of counting as no match, and `tests/test_harness.py` and `tests/test_gates.py` prove the harness and
every CI gate can fail.

## Finance scoping and the ERP schema

Sign-in, audit and ERP logs do not carry department or group membership. Finance rules use `|expand` placeholders,
filled from `pipelines/finance_scope.yml`. The values in that file are synthetic and must be replaced with your own
finance accounts and domains. Nothing in the raw logs is assumed to say who works in finance.

ERP rules use a vendor-neutral logsource (`product: erp`, services such as `vendor_master` and `payments`). The field
schema is in [docs/erp-log-schema.md](docs/erp-log-schema.md), the Splunk logsource mapping is
`pipelines/sigmafin_splunk.yml`, and Microsoft 365 field assumptions are in
[docs/m365-fields.md](docs/m365-fields.md). The schema is shaped like field-level ERP change records and payment
tables, but it has not been run against any ERP product, and SigmaFin makes no vendor-specific support claim.

## Limitations

- **Synthetic samples.** Every sample event is made up. Passing tests show the rule logic does what the author
  intended on those events, not that it fits real logs.
- **Tested on SQLite, shipped as SPL.** Tests run the SQLite conversion. The Splunk SPL is converted in CI but never
  executed. SQL and SPL differ (case handling, wildcards, boolean precedence), so SPL behaviour is unproven.
- **Generic ERP schema.** You must map your ERP audit data into it, and enrichment fields such as
  `outside_business_hours` must come from your pipeline.
- **Placeholder scoping.** Finance account and domain lists are placeholders that you maintain. Rules that cannot
  know what is new or unusual (for example a "new country" sign-in) use allowlists, not baselines.
- **Flattened M365 parameters.** Exchange `Parameters` must be flattened at ingestion. See docs/m365-fields.md.
- **Correlation support is uneven.** The SQLite backend converts all four correlation types. The Splunk backend 2.1.0
  does not convert `temporal_ordered`, so these rules have no SPL output and are listed in `scripts/policy.yml`:
  `erp_vendor_bank_change_then_payment`.
- **Standalone base rules.** pySigma suppresses a base rule that a correlation references unless `generate: true`.
  To deploy `erp_vendor_bank_details_changed` as its own alert, convert its file on its own. `build_spl.py` does so.
- **Validation is not coverage.** ATT&CK tags show intent. They do not prove a rule detects every procedure of the
  technique.

## License

MIT. See [LICENSE](LICENSE).
