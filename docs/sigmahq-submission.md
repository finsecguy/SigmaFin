# SigmaHQ submission

Prepared in this repository on 2026-11-22. Not submitted. No pull request was opened against
[SigmaHQ/sigma](https://github.com/SigmaHQ/sigma).

## Scope

The file glob `rules/bec_payment_fraud/m365_*` at the start of this note. Three rules. They are renamed below to
`microsoft365_*` and stay in `rules/bec_payment_fraud/`.

`m365_inbox_rule_change_event` is a rule name inside `entra_anonymous_signin_then_inbox_rule.yml`. That file does
not match the glob, so the support rule is outside this note.

Conventions checked, and only these:

- [SigmaHQ rule conventions](https://sigmahq.io/sigma-specification/sigmahq/sigmahq-rule-convention.html): `id`,
  `status`, `level`, `falsepositives`, `references`
- [SigmaHQ filename conventions](https://sigmahq.io/sigma-specification/sigmahq/sigmahq-filename-convention.html):
  product `m365` uses the `microsoft365_*` pattern
- [Sigma taxonomy](https://sigmahq.io/sigma-specification/specification/sigma-appendix-taxonomy.html): `product: m365`
  with `service: audit` is a listed logsource

## Summary

| Rule file (after the rename) | id | status | logsource | level | falsepositives | references | filename |
|---|---|---|---|---|---|---|---|
| `microsoft365_inbox_rule_external_forward_finance.yml` | meets | meets | meets | meets | meets | fixed | fixed |
| `microsoft365_inbox_rule_hides_finance_mail.yml` | meets | meets | meets | meets | meets | fixed | fixed |
| `microsoft365_mailbox_forwarding_external_finance.yml` | meets | meets | meets | meets | meets | fixed | fixed |

After the edits in this repository, all three meet the seven checks. The per-rule sections say what was already
true and what changed.

## What already met the conventions

**id.** Required, and a UUID version 4 is the form SigmaHQ expects. Each id below parses as version 4 with the
RFC 4122 variant, is lowercase, and is unique in this repository. None were changed.

**status.** A new SigmaHQ rule starts at `experimental`. All three were already `experimental`.

**logsource.** All three already set `product: m365` and `service: audit`, which the taxonomy lists for M365.

**level.** `high` and `medium` are allowed values.

- `m365_inbox_rule_external_forward_finance`: `high`
- `m365_inbox_rule_hides_finance_mail`: `medium`
- `m365_mailbox_forwarding_external_finance`: `high`

The related SigmaHQ hunting rule `c726e007-2cd0-4a55-abfb-79730fbedee5` is `medium`. That difference is a tuning
choice a reviewer might question. It is not a convention miss, so the levels were left as they are.

**falsepositives.** Each rule already lists specific operational cases (approved outsourcing, leave forwarding,
migrations, user filing rules). None use the rejected keywords `None`, `Pentest`, `Penetration Test`, or `Red Team`.

Titles are already title case, and each description already starts with "Detects". Those points are in the same
convention document and were already satisfied, so they were not edited.

## What each rule needed

### `microsoft365_inbox_rule_external_forward_finance.yml`

Rule `name`: `m365_inbox_rule_external_forward_finance`. Id `4b0f8f5e-2c6a-4d1e-9a47-3e5d7b1c9f20`.

- **references.** The list included `https://attack.mitre.org/techniques/T1114/003/`. SigmaHQ does not allow MITRE
  ATT&CK website links in `references`. The technique stays in the tags `attack.collection` and `attack.t1114.003`.
  The link was removed. The remaining references are `https://www.ic3.gov/CSA/2020/201204.pdf` and
  `https://www.ic3.gov/PSA/2020/PSA200406`.
- **filename.** The file was `m365_inbox_rule_external_forward_finance.yml`. The product pattern is
  `microsoft365_*`. Renamed to `microsoft365_inbox_rule_external_forward_finance.yml` (52 characters, inside the
  10 to 70 character filename length).

### `microsoft365_inbox_rule_hides_finance_mail.yml`

Rule `name`: `m365_inbox_rule_hides_finance_mail`. Id `8e3c1a57-6d24-4b9f-a0c8-5f27d9b4e611`.

- **references.** Removed `https://attack.mitre.org/techniques/T1564/008/`. The technique stays in the tags
  `attack.stealth` and `attack.t1564.008`. The remaining references are the Red Canary email hiding rules page, the
  Microsoft cookie-theft to BEC blog post from 2022-07-12, and the Microsoft Defender page on responding to a
  compromised email account.
- **filename.** Renamed from `m365_inbox_rule_hides_finance_mail.yml` to
  `microsoft365_inbox_rule_hides_finance_mail.yml` (46 characters).

### `microsoft365_mailbox_forwarding_external_finance.yml`

Rule `name`: `m365_mailbox_forwarding_external_finance`. Id `2d9a6b40-7c13-4e85-b1f6-0a4e8c3d5927`.

- **references.** Removed `https://attack.mitre.org/techniques/T1114/003/`. The technique stays in the tags
  `attack.collection` and `attack.t1114.003`. The remaining references are the Microsoft Defender compromised-account
  page, the Exchange Online forwarding documentation, and `https://www.ic3.gov/PSA/2020/PSA200406`.
- **filename.** Renamed from `m365_mailbox_forwarding_external_finance.yml` to
  `microsoft365_mailbox_forwarding_external_finance.yml` (52 characters).

Each edited rule has `modified: 2026-11-22`. `modified` is optional in the convention. It records this edit.

## Edits applied in this repository

- The three filenames now use the `microsoft365_*` prefix.
- The three `references` lists no longer contain `attack.mitre.org` links.
- `name` was not changed. Tests, correlations, and `scripts/policy.yml` key off `m365_*`.

## Still open before a SigmaHQ pull request

These items are outside the seven checks. They were not changed here, because changing them would change the
detection or this repository's layout. A copy made for SigmaHQ still needs them.

- **Placeholders.** All three rules expand `%finance_mailboxes%` and, where they check the recipient,
  `%internal_domains%` through `|expand` and `pipelines/finance_scope.yml`. SigmaHQ conversion does not load that
  pipeline. A submission copy has to replace the placeholders with something SigmaHQ can convert, or ship an
  equivalent pipeline the project will accept.
- **Flattened parameters.** The rules match `Parameters.<Name>`. The overlapping SigmaHQ rules match the serialized
  `Parameters` list with `|contains`. The descriptions already say the fields are flattened. A `logsource.definition`
  like the one on `microsoft365_susp_email_forwarding_activity.yml` would tell a reviewer that. It was not added,
  because `product` and `service` already match the taxonomy.
- **Filter names.** SigmaHQ recommends `filter_main_*` for mandatory exclusions and `filter_optional_*` for local
  ones. These rules use `filter_internal_*`. That recommendation was not applied, so the detection text stays
  aligned with the samples.
- **`name`.** SigmaHQ rules usually omit `name`. The field is allowed as a custom attribute. Drop it in the
  SigmaHQ copy if a reviewer asks. Keep it in this repository.
- **Directory.** SigmaHQ would place an `m365` / `audit` rule under `rules/cloud/m365/` or
  `rules-threat-hunting/cloud/m365/audit/` (the overlapping hunting rules use the second path). This repository
  keeps `rules/bec_payment_fraud/` because the test folders are `tests/<theme>/<rule name>/`. Move the file only in
  the upstream pull request. Which of the two SigmaHQ trees fits is a maintainer decision: these rules are narrower
  than the hunting rules, and they still document false positives.
