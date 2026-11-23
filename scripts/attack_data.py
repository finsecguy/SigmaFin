"""Point pySigma at the pinned MITRE files and warm its on-disk cache.

pySigma 1.5.1 downloads enterprise ATT&CK the first time code reads
``sigma.data.mitre_attack`` (see ``docs/attack-data.md``). ``sigma check`` has
no flag for a local file. It uses the default cache under
``~/.cache/pysigma/mitre_attack`` and downloads on a miss. ``set_url()`` is the
supported hook: it loads a local STIX file and writes that cache, so a later
``sigma check`` process does not open a network connection.

``sigma check`` also loads MITRE D3FEND for every tag, through the same kind of
hook. Both datasets are pinned.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATTACK_FILE = ROOT / "data" / "mitre" / "enterprise-attack.json"
D3FEND_FILE = ROOT / "data" / "mitre" / "d3fend.json"

# Collection version inside the pinned STIX, and the D3FEND ontology version.
# scripts/refresh_mitre_data.py prints the versions it downloaded. Update these
# constants in the same commit as a refreshed file.
EXPECTED_ATTACK_VERSION = "20.1"
EXPECTED_D3FEND_VERSION = "1.6.0"


def use_pinned_mitre() -> dict[str, str]:
    """Load both pinned files. Returns the versions pySigma parsed out."""
    from sigma.data import mitre_attack, mitre_d3fend

    mitre_attack.set_url(str(ATTACK_FILE))
    attack_version = str(mitre_attack.mitre_attack_version)
    mitre_d3fend.set_url(str(D3FEND_FILE))
    d3fend_version = str(mitre_d3fend.mitre_d3fend_version)
    return {"attack": attack_version, "d3fend": d3fend_version}


def main(argv: list[str] | None = None) -> int:
    del argv
    versions = use_pinned_mitre()
    print(f"MITRE ATT&CK {versions['attack']} from {ATTACK_FILE}")
    print(f"MITRE D3FEND {versions['d3fend']} from {D3FEND_FILE}")
    errors = []
    if versions["attack"] != EXPECTED_ATTACK_VERSION:
        errors.append(
            f"ATT&CK version is {versions['attack']}, expected {EXPECTED_ATTACK_VERSION}"
        )
    if versions["d3fend"] != EXPECTED_D3FEND_VERSION:
        errors.append(
            f"D3FEND version is {versions['d3fend']}, expected {EXPECTED_D3FEND_VERSION}"
        )
    for error in errors:
        print(f"ERROR {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
