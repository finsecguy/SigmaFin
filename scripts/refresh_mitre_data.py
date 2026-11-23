"""Download MITRE ATT&CK and D3FEND and rewrite the pinned files.

Not used by CI. CI reads data/mitre/ and must work with the network disabled.
Run this when you want a newer pin, then update EXPECTED_ATTACK_VERSION and
EXPECTED_D3FEND_VERSION in scripts/attack_data.py if the versions changed,
and read docs/attack-data.md.

The files this writes are reduced extracts. pySigma only reads the fields that
are kept. Full STIX descriptions are omitted so the pin stays small and so the
repository's em dash check is not tripped by MITRE prose.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ATTACK_FILE = ROOT / "data" / "mitre" / "enterprise-attack.json"
D3FEND_FILE = ROOT / "data" / "mitre" / "d3fend.json"
ATTACK_URL = (
    "https://github.com/mitre-attack/attack-stix-data/raw/refs/heads/master/"
    "enterprise-attack/enterprise-attack.json"
)
D3FEND_URL = "https://d3fend.mitre.org/ontologies/d3fend.json"
EM_DASH = "\u2014"

ATTACK_TYPES = {
    "x-mitre-collection",
    "x-mitre-tactic",
    "attack-pattern",
    "intrusion-set",
    "malware",
    "tool",
    "x-mitre-data-source",
    "course-of-action",
}


def _get(url: str) -> dict:
    with urlopen(url, timeout=120) as response:
        return json.load(response)


def _reduce_attack(raw: dict) -> dict:
    kept = []
    version = None
    for obj in raw.get("objects", []):
        if obj.get("type") not in ATTACK_TYPES:
            continue
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        slim: dict = {"type": obj["type"]}
        if obj["type"] == "x-mitre-collection":
            slim["name"] = obj.get("name")
            slim["x_mitre_version"] = obj.get("x_mitre_version")
            version = obj.get("x_mitre_version")
        else:
            if "name" in obj:
                slim["name"] = obj["name"]
            if "x_mitre_shortname" in obj:
                slim["x_mitre_shortname"] = obj["x_mitre_shortname"]
            refs = [
                {"source_name": "mitre-attack", "external_id": ref["external_id"]}
                for ref in obj.get("external_references", [])
                if ref.get("source_name") == "mitre-attack" and ref.get("external_id")
            ]
            if refs:
                slim["external_references"] = refs
            phases = [
                {"kill_chain_name": "mitre-attack", "phase_name": phase["phase_name"]}
                for phase in obj.get("kill_chain_phases", [])
                if phase.get("kill_chain_name") == "mitre-attack" and phase.get("phase_name")
            ]
            if phases:
                slim["kill_chain_phases"] = phases
        kept.append(slim)
    note = (
        "Reduced extract for pySigma's offline loader (sigma.data.mitre_attack.set_url). "
        f"Source: MITRE ATT&CK enterprise-attack STIX, collection version {version}. "
        "Keeps the collection version, tactics, techniques, groups, software and mitigations "
        "with ids, names and tactic phases only. Descriptions and relationships are omitted. "
        "Refresh with scripts/refresh_mitre_data.py. See docs/attack-data.md."
    )
    return {
        "type": "bundle",
        "id": raw.get("id"),
        "spec_version": raw.get("spec_version", "2.1"),
        "x_sigmafin_note": note,
        "objects": kept,
    }


def _reduce_d3fend(raw: dict) -> dict:
    graph = []
    version_iri = None
    for item in raw.get("@graph", []):
        if item.get("@type") == "owl:Ontology":
            version_iri = item.get("owl:versionIRI")
            break
    if not version_iri:
        raise RuntimeError("D3FEND ontology has no owl:Ontology versionIRI")
    graph.append({"@type": "owl:Ontology", "owl:versionIRI": version_iri})
    for item in raw.get("@graph", []):
        types = item.get("@type")
        type_list = types if isinstance(types, list) else ([types] if types else [])
        type_list = [str(t) for t in type_list]
        label = item.get("rdfs:label", "")
        d3id = item.get("d3f:d3fend-id", "")
        if isinstance(d3id, list):
            d3id = d3id[0] if d3id else ""
        if "d3f:DefensiveTactic" in type_list and label:
            graph.append(
                {
                    "@id": item.get("@id", ""),
                    "@type": ["d3f:DefensiveTactic"],
                    "rdfs:label": label,
                }
            )
        elif isinstance(d3id, str) and d3id.startswith("D3-") and label:
            graph.append(
                {
                    "@id": item.get("@id", ""),
                    "@type": type_list[:1] or ["d3f:DefensiveTechnique"],
                    "rdfs:label": label,
                    "d3f:d3fend-id": d3id,
                }
            )
    return {
        "@graph": graph,
        "x_sigmafin_note": (
            "Reduced extract for pySigma's offline loader (sigma.data.mitre_d3fend.set_url). "
            f"Source: {D3FEND_URL}. "
            "Keeps the ontology version, defensive tactics and technique ids and labels. "
            "Digital artifacts are omitted because no SigmaFin rule uses a d3fend tag. "
            "sigma check still loads this dataset for every tag, so the file is pinned to avoid a download. "
            "Refresh with scripts/refresh_mitre_data.py. See docs/attack-data.md."
        ),
    }


def _write(path: Path, payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if EM_DASH in text:
        raise RuntimeError(f"{path.name} would contain an em dash; refusing to write")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    print(f"GET {ATTACK_URL}")
    attack = _reduce_attack(_get(ATTACK_URL))
    _write(ATTACK_FILE, attack)
    version = next(
        obj.get("x_mitre_version")
        for obj in attack["objects"]
        if obj.get("type") == "x-mitre-collection"
    )
    print(f"wrote {ATTACK_FILE} version {version} objects {len(attack['objects'])}")

    print(f"GET {D3FEND_URL}")
    d3fend = _reduce_d3fend(_get(D3FEND_URL))
    _write(D3FEND_FILE, d3fend)
    print(f"wrote {D3FEND_FILE} graph items {len(d3fend['@graph'])}")
    print(
        "If either version changed, update EXPECTED_ATTACK_VERSION and "
        "EXPECTED_D3FEND_VERSION in scripts/attack_data.py and the dates in docs/attack-data.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
