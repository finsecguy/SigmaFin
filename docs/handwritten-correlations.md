# Hand-written correlation queries

pySigma's Splunk backend 2.1.0 does not convert `temporal_ordered` correlations.
The Kusto backend 1.0.1 does not convert any correlation. Those rules are tested
on the SQLite backend and listed under `splunk_unsupported` and
`kusto_unsupported` in `scripts/policy.yml`. The files in
[handwritten/](handwritten/) are hand-written substitutes. They are not output
from `scripts/build_spl.py` or `scripts/build_kql.py`, and CI does not regenerate
them.

`tests/test_handwritten.py` checks that every rule in those policy lists has the
expected file, that the file says it is hand-written, and that the rule id, the
Sigma timespan and the group-by fields appear in it. It also checks that the
Entra correlation still names every user in `pipelines/finance_scope.yml`. A
failure means the query was not updated with the rule.

## Which file is which

| Rule | Id | Sigma window | Files |
|---|---|---|---|
| `erp_vendor_bank_change_then_payment` | `6a1f4c8e-0b25-4e93-a7d3-9c2b5e8f1a64` | `temporal_ordered`, 3 days, group by `vendor_id` | `.spl` and `.kql` |
| `erp_new_vendor_paid_quickly` | `77b79c4a-42a8-4dd5-b6ab-98e2aa76b450` | `temporal_ordered`, 3 days, group by `vendor_id` | `.spl` and `.kql` |
| `entra_anonymous_signin_then_inbox_rule` | `c3f8a1d6-2e59-4b70-8a4c-6d0e9b7f1235` | `temporal_ordered`, 1 hour, group by `user` | `.spl` and `.kql` |
| `erp_vendor_created_and_payment_approved_by_same_user` | `e61a55ef-585a-4b7e-bc43-f0558626f3d5` | `temporal` (unordered), 30 days, group by `vendor_id` and `user` | `.kql` only |

The last rule already converts to SPL. That generated query bins time into fixed
30 day windows and can miss a pair that crosses a bin edge. The prediction is in
[splunk-expectations.md](splunk-expectations.md). The hand-written KQL uses a
sliding 30 day distance instead, which is what the SQLite tests check. Do not
"correct" the KQL to match the generated SPL.

`erp_new_vendor_paid_quickly` is the rule for a vendor created and then paid.
There is no rule named `erp_new_vendor_created_then_paid`.

## Field names

The queries use the SigmaFin field names, not the SAP columns in
[sap-mapping.md](sap-mapping.md). Assumed Splunk sourcetypes are the ones in
`pipelines/sigmafin_splunk.yml`. Assumed Sentinel tables are the ones in
`pipelines/sigmafin_kusto.yml`. `_time` (SPL) and `TimeGenerated` (KQL) must be
the Sigma `timestamp`. If a collector stores that time only in another column,
change the query.

For the Entra correlation the join key is the Sigma alias `user`:
`UserPrincipalName` on the sign-in and `UserId` on the audit event. The finance
user list is copied from `finance_users` in `pipelines/finance_scope.yml`. Those
values are synthetic. Replace them with the real accounts before use.

SAP column names, if the data is native ECC or S/4HANA rather than the
vendor-neutral schema, are in [sap-mapping.md](sap-mapping.md). Substitute them
per source. `vendor_id` is not the same column on a change document and on
`REGUH`.

## Window logic

`temporal_ordered` means: an event of the first referenced rule, then an event
of the second, same group-by values, second timestamp strictly after the first,
difference at most the timespan. The queries implement that with a join and a
time comparison, not with Splunk `bin`. That matches the SQLite tests, which use
a sliding window.

Splunk `join` subsearches are capped (`maxout`). A finance tenant with a modest
event rate fits. An unfiltered payment extract can silently drop rows. If the
subsearch truncates, rewrite the search as a single pass that stats the two
timestamps without a subsearch.

`temporal` (the segregation-of-duties rule) is unordered: both events inside the
timespan, same `vendor_id` and same `user`. The KQL uses the absolute time
difference.

## Keeping them in sync

When a Sigma correlation changes, update the matching file in the same commit:

- timespan (`3d`, `1h`, `30d` must still appear, because the test looks for the Sigma value)
- group-by fields
- detection values of the referenced rules (actions, bank field names, operations, risk type)
- the finance user list, for the Entra rule
- the rule id, if it ever changes

The header of each file repeats the id, the timespan and the assumption. Lines
that start with `#` (SPL files) or `//` (KQL files) are labels for people. They
are not SPL. Paste from the first search or table line.
