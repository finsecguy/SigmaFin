# SigmaFin

[![CI](https://github.com/finsecguy/SigmaFin/actions/workflows/ci.yml/badge.svg)](https://github.com/finsecguy/SigmaFin/actions/workflows/ci.yml)

SigmaFin is a collection of Sigma detection rules for threats against corporate finance departments: business email
compromise, vendor and payment manipulation, privileged ERP abuse, finance data theft and account takeover of finance
staff. It is for detection engineers and SOC teams who protect those departments and want rules that are validated,
tested against sample events and honest about what they do not prove.

The project is a work in progress. The rule table below lists what is built today, and the [roadmap](#roadmap) lists
what is planned.

## Why finance departments

Finance teams run a small number of processes where one fraudulent change moves real money:

| Process | What it covers | How it gets attacked |
|---|---|---|
| Accounts payable | Invoice intake, approval and payment to suppliers | Mailbox takeover to read and alter payment conversations, fake or fast-paid vendors |
| Vendor master data | Supplier records and their bank details | Bank detail changes that redirect payments, vendors created and paid by the same person |
| Treasury and payments | Payment runs, releases, bank connectivity | Tampering with payment runs, takeover of approvers' accounts |
| Payroll | Employee pay data and payroll mailboxes | Forwarded payroll mail, bulk payroll downloads |
| Financial reporting | Ledgers, close and pre-release results | Direct table edits, early access to results, pasting results into public AI chat services |

Generic rule sets tend to miss these for structural reasons, not because they are poorly written:

- Much of the fraud uses legitimate business functions. A vendor bank change is an ordinary ERP action, so no
  malware, exploit or odd process exists to detect. The signal is the sequence and context of business events.
- ERP audit data has no standard Sigma logsource. In the SigmaHQ checkout used for the [overlap check](#sigmahq-overlap)
  (commit `f083329`), searches for vendor, bank account and accounts payable terms found no ERP rules.
- Sign-in and audit logs do not say who works in finance, so a generic rule cannot tell a finance mailbox from any
  other. SigmaFin handles this with explicit lists (see [finance scoping](#finance-scoping)).
- Several detections need correlation across events, such as a bank change followed by a payment to the same vendor.

## Rule catalog

The table is generated from the rule files by `scripts/gen_docs.py`. Do not edit it by hand: CI fails if it is out
of date. Per-rule SigmaHQ overlap decisions are in [docs/rule-catalog.md](docs/rule-catalog.md) and the technique
table is in [docs/attack-coverage.md](docs/attack-coverage.md). "Fraud, no technique" means no clean ATT&CK mapping
exists, and the rule's description says so.

<!-- RULES:START -->
| Rule | Theme | ATT&CK technique | Log source | Level | Notes |
|---|---|---|---|---|---|
| Finance Account Signs In From Anonymous IP Address (`entra_finance_signin_anonymous_ip`) | 1. BEC and payment fraud | T1078.004 Cloud Accounts, T1090.003 Multi-hop Proxy | azure/signinlogs | medium |  |
| Finance Account Sign-in From Country Outside Allowed List (`entra_finance_signin_unlisted_country`) | 1. BEC and payment fraud | T1078.004 Cloud Accounts | azure/signinlogs | medium |  |
| Finance Mailbox Inbox Rule Forwards Mail to External Address (`m365_inbox_rule_external_forward_finance`) | 1. BEC and payment fraud | T1114.003 Email Forwarding Rule | m365/audit | high |  |
| Finance Mailbox Inbox Rule Hides or Deletes Finance Keyword Mail (`m365_inbox_rule_hides_finance_mail`) | 1. BEC and payment fraud | T1564.008 Email Hiding Rules | m365/audit | medium |  |
| Finance Mailbox Forwarding Set to External Address (`m365_mailbox_forwarding_external_finance`) | 1. BEC and payment fraud | T1114.003 Email Forwarding Rule | m365/audit | high |  |
| Vendor Bank Details Changed (Correlation Input) (`erp_vendor_bank_change_event`) | 2. Vendor and payment manipulation (ERP) | none (support rule) | erp/vendor_master | informational | Support rule, not deployed alone |
| Vendor Bank Details Changed Then Payment Released (`erp_vendor_bank_change_then_payment`) | 2. Vendor and payment manipulation (ERP) | T1657 Financial Theft | erp/vendor_master + erp/payments | high | Sigma + SQLite tested, no SPL (Splunk backend lacks temporal_ordered) |
| Vendor Master Bank Details Changed (`erp_vendor_bank_details_changed`) | 2. Vendor and payment manipulation (ERP) | T1657 Financial Theft | erp/vendor_master | medium |  |
| Vendor Payment Released (`erp_vendor_payment_released`) | 2. Vendor and payment manipulation (ERP) | none (support rule) | erp/payments | informational | Support rule, not deployed alone |
<!-- RULES:END -->

What each theme protects:

1. **BEC and payment fraud.** Detects the mailbox changes attackers make after taking over a finance account to watch
   or divert payment conversations.
2. **Vendor and payment manipulation (ERP).** Detects vendor bank detail changes, payments that follow them and, in
   later rules, segregation-of-duties breaks and out-of-hours payment run changes.
3. **Privileged ERP and finance app abuse.** Planned: emergency access, new privileged roles, debug or direct table
   edits and out-of-process user creation.
4. **Finance data exfiltration and insider risk.** Planned: bulk exports, large payroll and statement downloads,
   uploads to personal cloud storage and unusual access to pre-release results.
5. **Account takeover of finance staff.** Planned: MFA fatigue, MFA method changes and risky OAuth consent grants.
6. **Data leakage to AI services.** Planned, and only if credible public sources are found (see roadmap).

## Quick start

Requires Python 3.12 or newer. CI runs 3.12 and 3.14. These commands were run in a Python 3.12 virtual environment.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

sigma check --fail-on-issues --fail-on-error rules   # Sigma validation
python scripts/check_metadata.py                     # references, tags, ids, samples, mirrors
python -m pytest -q tests                            # sample tests, harness and gate self-tests
python scripts/build_spl.py                          # Splunk SPL into build/spl/
```

Other commands:

```bash
python scripts/gen_docs.py            # regenerate the README table and docs/ catalog files
python scripts/gen_docs.py --check    # fail if they are out of date
python scripts/check_no_em_dash.py    # the repository uses no em dashes
```

To convert one rule yourself, pass the pipelines it needs. This prints SPL:

```bash
sigma convert -t splunk -p pipelines/finance_scope.yml -p pipelines/sigmafin_splunk.yml \
  rules/bec_payment_fraud/m365_inbox_rule_external_forward_finance.yml
```

A rule that uses a finance scope placeholder fails loudly if `finance_scope.yml` is missing ("unhandled placeholder")
instead of silently producing an unscoped query.

## Log sources and schemas

| Source | Rules use | Notes |
|---|---|---|
| Microsoft 365 audit and Exchange admin audit | `product: m365`, `service: audit` | Needs the `Parameters` flattening below |
| Microsoft Entra sign-in logs | `product: azure`, `service: signinlogs` | Column names of the `SigninLogs` table, see [docs/entra-fields.md](docs/entra-fields.md) |
| ERP application audit | `product: erp`, `service: vendor_master` or `payments` | Custom, vendor-neutral logsource |

Planned sources not yet used by any rule: Entra ID audit logs, proxy and DNS logs, Sysmon on finance
workstations, and the reserved ERP services `user_admin`, `system_audit` and `reporting`.

**ERP logsource.** Sigma has almost no ERP coverage, so SigmaFin defines its own logsource and field schema in
[docs/erp-log-schema.md](docs/erp-log-schema.md). It is shaped like field-level change records (object, field, old
value, new value) plus payment records. You map your ERP audit data into it. No ERP product has been tested, and
SigmaFin makes no vendor-specific support claim. `pipelines/sigmafin_splunk.yml` maps the logsources to Splunk
sourcetypes. The sourcetype names are placeholders you should change.

**Business hours field.** Sigma has no time-of-day condition. Rules that need one read a precomputed
`outside_business_hours` field (`true` or `false`) that your ingestion or enrichment step must populate from the
event time, time zone, working calendar and holidays. SigmaFin does not compute it. No current rule uses it.

**M365 `Parameters` flattening.** Exchange admin audit records carry `Parameters` as a list of name and value pairs,
which Sigma cannot match inside. Rules expect one field per parameter, named `Parameters.<Name>` (for example
`Parameters.ForwardTo`), with one recipient per field or per event. You must do this at ingestion. SigmaFin does not
ship the normalization. Details: [docs/m365-fields.md](docs/m365-fields.md).

## Finance scoping

Sign-in, audit and ERP logs do not carry department or group membership, so SigmaFin does not pretend they do. Finance
rules scope with placeholder lists, using Sigma's `|expand` modifier:

```yaml
UserId|expand: '%finance_mailboxes%'
Parameters.ForwardTo|endswith|expand: '%internal_domains%'
```

The lists live in `pipelines/finance_scope.yml` as pipeline `vars`, and a `value_placeholders` transformation fills
them in at conversion time. The shipped values are **synthetic placeholders** on reserved example domains
(`finance.example.com`, `corp.example.com`). They are also what the tests use.

To use the rules for real:

1. Copy `pipelines/finance_scope.yml` and replace `finance_mailboxes` with your finance user principal names and
   shared mailboxes (AP, treasury, payroll), and `internal_domains` with your recipient domains, written with a
   leading `@` because the match is on the end of the value.
2. Pass your copy with `-p` when you convert (see the `sigma convert` example above).
3. Keep the lists current. A leaver or a new shared mailbox that is not in the list is outside the rule's scope.

An enrichment field (a department or group attribute added at ingestion) would also work, and would let you replace
the placeholder with a field condition. The shipped rules do not assume such a field exists.

## Testing approach

Tests convert the real rule files, not a copy of their logic.

- **SQLite backend.** `tests/test_rules.py` converts each rule with the pySigma SQLite backend, loads each sample
  into an in-memory SQLite table and runs the query. Positive samples must match and negative samples must not.
  Samples live in `tests/<theme>/<rule_name>/{positive,negative}/*.json`. A sample is one flat event or a list of
  events with an ISO 8601 `timestamp`. Negative samples are written as near misses.
- **No silent passes.** A SQL error or an unparseable timestamp fails the test instead of counting as "no match".
  A field that no sample contains becomes a NULL column, so a missing field cannot make a query error out and pass.
  `tests/test_harness.py` proves the harness fails when a rule is broken or a negative matches.
- **Correlation on a real backend.** The SQLite backend converts all four correlation types, so correlation rules are
  run over timestamped event lists, including ordering and window edge cases. No custom evaluator is used.
- **Whole-directory conversion.** `tests/test_whole_directory.py` converts all of `rules/` in one run and checks that
  every alerting rule is still output. pySigma drops a rule that a correlation references, so this catches a
  correlation silently hiding a standalone alert.
- **Support-rule drift gate.** Each correlation uses its own non-alerting support copy of the conditions it needs. A
  `mirrors` entry in `scripts/policy.yml` makes `check_metadata.py` fail if a support copy's logsource or detection
  differs from the standalone rule it copies.
- **Known gaps.** `tests/known_gaps/` holds events a rule should flag but currently misses.
  `tests/test_known_gaps.py` asserts the miss, so a gap stays visible and the test fails when the rule is fixed.

What the tests do not do: they apply only `finance_scope.yml`, so the logsource mapping in `sigmafin_splunk.yml` is not
exercised, and nothing checks sample field names against the schema documents.

## CI gates

CI (`.github/workflows/ci.yml`) runs on every push and pull request, on Python 3.12 and 3.14. The steps:

| Gate | Fails on | Self-tested |
|---|---|---|
| `check_no_em_dash.py` | Any em dash in a tracked or untracked non-ignored text file | Yes, on a file with and without one |
| `check_metadata.py` | Missing required fields, bad UUID, non-HTTPS or missing references, duplicate id or name, missing technique tag (unless listed in `scripts/policy.yml`), missing tactic tag, unresolved correlation reference, missing positive or negative sample, support rule drift | Partly: missing references, technique tag, tactic tag, negative sample, duplicate id and support rule drift are tested. The other checks are not |
| `sigma check --fail-on-issues --fail-on-error` | Parse errors and any validator issue, including unknown ATT&CK techniques and tactics | Partly: unknown technique and unknown tactic are tested |
| `pytest` | Failing positive or negative samples, harness checks, known gap checks, whole-directory checks | The harness is self-tested. The sample tests themselves are not |
| `gen_docs.py --check` | README table or generated docs out of date | Yes |
| `build_spl.py` | A rule fails to convert and is not listed as unsupported, or a listed rule now converts | Yes, both directions |
| Artifact upload | Not a gate. Publishes `build/spl` as the `splunk-spl` artifact from the 3.12 job | No |

Rule metadata is also covered only as far as these checks go. References are checked for presence and HTTPS, not for
whether the URL resolves or supports the rule. That was done by hand when each rule was written.

## Limitations

- **SPL is converted but never executed against Splunk.** Tests run the SQLite conversion. The SPL is only generated
  and published as a CI artifact. SQL and SPL differ in case handling, wildcards and boolean precedence, so SPL
  behaviour is unproven.
- **`temporal_ordered` rules have no SPL output.** The pySigma Splunk backend 2.1.0 cannot convert that correlation
  type. These rules keep strict event ordering, are tested on SQLite only and are marked in the table. They are listed
  in `scripts/policy.yml`, and CI fails if the list goes stale.
- **Samples are synthetic.** Every event is made up. Passing tests show the rule logic does what the author intended
  on those events, not that it fits real telemetry or finds real attacks.
- **The ERP schema is generic.** You must map your ERP audit data into it, and no vendor-specific mapping or support
  has been tested.
- **Allowlist-based rules cannot find "new" behaviour without tuning.** Rules scoped by lists (finance accounts,
  internal domains, allowed countries) only know what the lists say. Detecting a first-seen country or an unusual
  user needs a baseline that Sigma cannot express.
- **Known M365 forwarding gap.** `m365_inbox_rule_external_forward_finance` judges only the end of a field value. If
  one field holds several recipients and the last is internal, an earlier external recipient is missed. Ingest one
  recipient per field or per event. The gap is asserted in `tests/known_gaps/`.
- **Known inbox rule hiding gap.** `m365_inbox_rule_hides_finance_mail` requires a finance keyword. A hiding rule that
  selects mail by sender only is missed. The gap is asserted in `tests/known_gaps/`.
- **Country rule is a list, not a baseline.** `entra_finance_signin_unlisted_country` alerts on "outside the list", not
  on "new for this user".
- **Anonymous IP rule relies on Microsoft's classification.** `entra_finance_signin_anonymous_ip` sees only addresses
  Microsoft flags as anonymous.
- **ATT&CK tags show intent, not coverage.** A tag does not mean the rule detects every procedure of the technique.
- **CI has to pass on GitHub to count.** The badge at the top shows the state of the latest run.

## SigmaHQ overlap

Before each rule was written, the SigmaHQ repository (`rules`, `rules-threat-hunting` and `rules-emerging-threats`,
commit `f083329`, 2026-10-19) was searched for an equivalent. The terms, matches and decisions are recorded in
[docs/sigmahq_overlap.yml](docs/sigmahq_overlap.yml) and rendered in [docs/rule-catalog.md](docs/rule-catalog.md).

- `m365_inbox_rule_external_forward_finance` overlaps a SigmaHQ threat hunting rule
  (`c726e007-2cd0-4a55-abfb-79730fbedee5`) that matches any forwarding parameter. SigmaFin keeps its rule scoped:
  it adds a finance account list and an external recipient check, which the SigmaHQ rule does not have. Two other
  SigmaHQ rules are related but differ in what they match or in log source.
- The vendor bank change rule, the payment support rule and the bank change then payment correlation have no
  equivalent in SigmaHQ for the terms searched.

Only rules that exist have been checked. Each new rule gets the same check first.

## Version pins

`requirements.txt` pins exact versions:

| Package | Version |
|---|---|
| pySigma | 1.5.1 |
| pysigma-backend-sqlite | 2.0.0 |
| pysigma-backend-splunk | 2.1.0 |
| sigma-cli | 3.1.0 |

sigma-cli 3.1.0 requires pySigma below 2.0, and the newer SQLite backend (2.1.x) requires pySigma 2.0.1 or newer, so
the two cannot be installed together. The set above was verified to install and pass every gate. Revisit the pins when
a sigma-cli release supports pySigma 2.x.

## Roadmap

Planned rules by theme. Titles are not commitments: each rule needs a real public source and a SigmaHQ overlap check
first, and a rule without a credible source is dropped.

- **BEC and payment fraud:** inbox rules that hide finance mail, mailbox-level forwarding to external addresses
  (likely to overlap a SigmaHQ rule heavily), finance sign-ins from non-allowlisted countries, finance sign-ins from
  anonymising infrastructure, and a correlation of that sign-in followed by an inbox rule.
- **Vendor and payment manipulation:** new vendor created then paid quickly (correlation), payment run changes outside
  business hours (needs the business-hours field), and one user creating a vendor and approving its payment.
- **Privileged ERP and finance app abuse:** emergency access use, new privileged roles, debug or direct table edits,
  and user creation outside the identity process.
- **Finance data exfiltration and insider risk:** bulk ERP exports, large payroll or statement downloads, uploads to
  personal cloud storage, archive tools on finance workstations, and pre-release results access by unlisted users.
- **Account takeover of finance staff:** MFA fatigue, MFA fatigue followed by a successful sign-in, MFA method changes
  and risky OAuth consent grants.
- **Data leakage to AI services:** uploads of finance documents to public AI chat services in proxy logs. This stays
  only if credible sources are found (the OWASP Top 10 for LLM Applications on sensitive information disclosure and a
  documented real-world incident); otherwise it is dropped.

Also planned: executing the generated SPL against a local Splunk instance, so SPL behaviour can be tested and not only
converted.

## AI use

This project was built with AI assistance (Claude and Claude Code). AI was used to research threat references and Sigma
and pySigma documentation, and to draft the rules, tests, scripts, CI configuration and documentation.

### Author's role

Herman Kaufman directed the project and made its decisions:

- Defined the project: a standalone Sigma rule set for corporate finance departments.
- Set the requirements: synthetic data only, real public references for every rule, no claims beyond what tests prove,
  and validation against the official Sigma specification.
- Reviewed the proposed rule list, cut and restructured rules, and required a SigmaHQ overlap check for each one.
- Chose the finance scoping approach (documented allowlists and enrichment fields) and the ERP schema assumptions, such
  as the business-hours field.
- Decided to keep strict event ordering for correlation rules, accepting the loss of SPL output over weaker detection
  logic.
- Required the safeguards that keep the rules honest: decoupling the standalone alert from its correlation, the
  support-rule drift gate, the whole-directory conversion test, and tests documenting known detection gaps.
- Set the testing and CI standards, including the Python 3.12 and 3.14 matrix.
- Reviewed each stage's results before approving the next, and handles all publishing to GitHub.

Every rule is checked by the automated tests and CI gates described above.

## License and author

Released under the [MIT License](LICENSE).

Author: Herman Kaufman. GitHub: [github.com/finsecguy](https://github.com/finsecguy). Blog: [FinSecGuy blog](https://substack.com/@finsecguy).
