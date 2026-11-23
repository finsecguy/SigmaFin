# Changelog

All notable changes to SigmaFin are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers follow semantic
versioning. This file is the version record. It is not a GitHub release, and this repository has no release tags.

## [Unreleased]

### Added

- `pipelines/sap_erp.yml` maps the vendor-neutral ERP schema onto SAP ECC and S/4HANA change documents,
  payment-run tables and role assignments. Gaps are written down in `docs/sap-mapping.md`. The vendor bank
  change rule is converted in CI and matched against local fixtures.
- Hand-written Splunk SPL and Sentinel KQL for correlation rules the pySigma backends cannot convert
  (`docs/handwritten/`, index in `docs/handwritten-correlations.md`).
- Pinned MITRE ATT&CK 20.1 and D3FEND 1.6.0 under `data/mitre/`, loaded through pySigma's `set_url()` hook so
  CI does not download them. Refresh steps are in `docs/attack-data.md`.

### Changed

- Rule `author` values and the LICENSE copyright holder are Herman K. (finsecguy).

## [0.1.0] - 2026-11-22

### Added

- Sigma rules for business email compromise and payment fraud, vendor and payment manipulation, and privileged ERP
  abuse, with positive and negative samples and a SQLite test harness.
- Splunk SPL generation (`scripts/build_spl.py`, output under `build/spl/`).
- Microsoft Sentinel and Defender KQL generation with pySigma and pysigma-backend-kusto 1.0.1
  (`scripts/build_kql.py`, output under `build/kql/`). Support rules, the unsupported list, and the summary file
  follow the SPL build. Generated queries stay out of git because `build/` is ignored, and CI uploads them.
- Continuous integration (`.github/workflows/ci.yml`) that runs `sigma check --fail-on-issues --fail-on-error` and
  requires conversion to both SPL and KQL to succeed. Actions are pinned to commit SHAs. The workflow permission is
  `contents: read`.
- `docs/sigmahq-submission.md`, notes for a future SigmaHQ contribution. Nothing has been submitted.

### Changed

- The three `rules/bec_payment_fraud/m365_*` files are renamed to the SigmaHQ `microsoft365_*` filename pattern.
  The rule `name` values stay `m365_*` so tests, correlations, and `scripts/policy.yml` keep their keys.
- MITRE ATT&CK website links were removed from those rules' `references`. The techniques remain in `tags`, which is
  how the SigmaHQ reference convention records ATT&CK.
