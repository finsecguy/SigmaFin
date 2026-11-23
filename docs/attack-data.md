# Pinned MITRE data

pySigma 1.5.1 does not ship ATT&CK. The first read of `sigma.data.mitre_attack`
downloads enterprise ATT&CK STIX from GitHub and stores the parsed result in
`~/.cache/pysigma/mitre_attack`. `sigma check` validates `attack.*` tags against
that data. It also loads MITRE D3FEND on every tag (`sigma.data.mitre_d3fend`),
even though no SigmaFin rule uses a `d3fend` tag. Neither `sigma check` nor the
library reads an environment variable for the path. The supported hook is
`set_url()` on each module, which accepts a local file and rewrites the cache.

## What is pinned

| File | Dataset | Version | What was kept |
|---|---|---|---|
| `data/mitre/enterprise-attack.json` | Enterprise ATT&CK STIX | 20.1 | Collection version, tactics, techniques, groups, software, mitigations. Ids, names and tactic phases only. |
| `data/mitre/d3fend.json` | D3FEND ontology | 1.6.0 | Ontology version, defensive tactics, technique ids and labels. Artifacts omitted. |

ATT&CK 20.1 was taken from `attack-stix-data` commit `a8db2f52eb933c9c99060c123e088b3326d3a607` (master, 2026-11-05) and saved on 2026-11-23. The source URL is the `master` branch file `enterprise-attack/enterprise-attack.json`. D3FEND 1.6.0 was saved the same day from `https://d3fend.mitre.org/ontologies/d3fend.json`.

Descriptions are not stored. pySigma does not read them, and the upstream prose contains em dashes, which this repository rejects. `scripts/refresh_mitre_data.py` refuses to write a file that contains an em dash.

Tactic shortname `stealth` (not `defense-evasion`) is what version 20.1 publishes for Defense Evasion. Rules use `attack.stealth` because that is the string `sigma check` accepts.

## How CI uses it

`scripts/attack_data.py` calls `set_url()` for both files and reads one attribute so the default cache is filled. CI runs that script before `sigma check`. A later process in the same job finds the cache and does not download.

`scripts/gen_docs.py` calls the same function before it imports technique names, so a cold cache still resolves names from the file.

Expected versions are constants in `scripts/attack_data.py` (`EXPECTED_ATTACK_VERSION`, `EXPECTED_D3FEND_VERSION`). The script exits non-zero if the file parses as a different version.

## Refresh

From a machine that can reach GitHub and d3fend.mitre.org:

```bash
python scripts/refresh_mitre_data.py
python scripts/attack_data.py
```

If the printed ATT&CK or D3FEND version changed, update the two constants and the version table in this file in the same commit. Then run `python scripts/gen_docs.py`. Technique display names in `docs/attack-coverage.md` come from the pin. A renamed technique makes that file stale until it is regenerated.

Do not point `set_url()` at the upstream URL in CI. That is the download this pin exists to avoid.
