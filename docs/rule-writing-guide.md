# Rule writing guide

1. **Check SigmaHQ first.** Search `rules`, `rules-threat-hunting` and `rules-emerging-threats` for an equivalent.
   Record the terms, the result and the decision in `docs/sigmahq_overlap.yml`. If one exists, drop the rule or state
   in the description what finance scoping adds.
2. **Find a real source.** Every rule needs at least one reference you opened and read: an ATT&CK page, vendor report,
   regulator or FBI IC3 advisory, or DFIR write-up. If you cannot find one, drop the idea.
3. **Metadata.** `title`, `id` (UUID), `name` (unique snake_case, used by correlations and for the test folder),
   `status`, `description`, `author`, `date`, `references`, `level`, `falsepositives`, `logsource`.
4. **Tags.** Add `attack.<tactic>` and `attack.tNNNN`. Tactic names must exist in the ATT&CK data bundled with
   the installed pySigma (this version uses `stealth`, not `defense-evasion`). For business-process fraud with no
   technique, list the rule in `scripts/policy.yml` with a reason, and write "No ATT&CK technique applies" in the
   description.
5. **Scoping.** Use `|expand` placeholders from `pipelines/finance_scope.yml` for finance account lists. Do not imply
   the raw log carries department.
6. **Samples.** Add at least one JSON file under `tests/<theme>/<name>/positive/` and `negative/`. A sample is one
   flat event object or a list of them, each with an ISO 8601 `timestamp`. Make negatives near misses (right action,
   wrong field; right events, wrong order or window).
7. **Correlation.** Put support rules and the correlation in the same file as separate YAML documents. Give each
   correlation its own support rules: a support rule shared by two correlations makes pySigma fail when the whole
   `rules/` directory is converted ("Conversion state not available"), so copy it and list the copy under `mirrors`.
   Give the support rules `status`, tests and a `support_rules` entry in `policy.yml`. The SQLite backend converts
   `event_count`, `value_count`, `temporal` and `temporal_ordered`; the Splunk backend 2.1.0 does not convert
   `temporal_ordered`.
8. **Run everything.** `sigma check -i rules`, `pytest`, `python scripts/gen_docs.py`, `python scripts/build_spl.py`.
9. **No em dashes** in docs, comments or commit messages. CI enforces this.
