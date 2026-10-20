# Expected differences between SQLite and Splunk

The SQLite tests pass for every rule below. The generated SPL has not been executed anywhere yet. This file records
where the SPL is *expected* to behave differently, so the Splunk lab check (a manual phase, not CI) can confirm or
refute each prediction. A prediction here is not a result.

| Rule | Sample | SQLite | SPL expectation |
|---|---|---|---|
| `erp_vendor_created_and_payment_approved_by_same_user` | `tests/erp_vendor_payment/erp_vendor_created_and_payment_approved_by_same_user/positive/straddles_30d_bin_boundary.json` | Matches (sliding 30 day window, events 1 day apart) | SPL expected to miss (`bin _time span=30d`) |

## Why the SPL is expected to miss

The pySigma Splunk backend converts the `temporal` correlation to a `multisearch`, then `bin _time span=30d`, then
`stats dc(event_type) by _time vendor_id user`. That groups events into fixed 30 day bins. Two events one day apart
that fall on either side of a bin edge land in different bins, so neither bin sees both event types.

The sample puts the vendor creation at `2026-03-07T12:00:00Z` and the approval at `2026-03-08T12:00:00Z`. If bins are
aligned to the Unix epoch, `2026-03-08T00:00:00Z` is a bin edge (684 times 2592000 seconds). That alignment is an
assumption: the lab run should show how Splunk actually aligns the bins before the result is trusted.

If the lab shows the SPL does match, the prediction is wrong and this file and the rule description must be
corrected. If it misses, the limitation becomes a confirmed gap and should move to the README limitations.
