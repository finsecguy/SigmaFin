"""Pinned MITRE data loads, and a dead proxy cannot force a download."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import attack_data  # noqa: E402


def test_pinned_versions_match_constants():
    assert attack_data.main() == 0


def test_pinned_files_load_when_urlopen_is_blocked(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("urlopen was called")

    import sigma.data.mitre_attack as attack_mod
    import sigma.data.mitre_d3fend as d3fend_mod

    monkeypatch.setattr(attack_mod, "urlopen", boom)
    monkeypatch.setattr(d3fend_mod, "urlopen", boom)
    versions = attack_data.use_pinned_mitre()
    from sigma.data import mitre_attack

    assert versions["attack"] == attack_data.EXPECTED_ATTACK_VERSION
    assert versions["d3fend"] == attack_data.EXPECTED_D3FEND_VERSION
    assert mitre_attack.mitre_attack_techniques["T1657"] == "Financial Theft"
    assert "T9999" not in mitre_attack.mitre_attack_techniques
    assert "stealth" in mitre_attack.mitre_attack_tactics.values()


def test_sigma_check_uses_the_cache_when_the_proxy_is_dead():
    attack_data.use_pinned_mitre()
    env = os.environ.copy()
    env["http_proxy"] = "http://127.0.0.1:9"
    env["https_proxy"] = "http://127.0.0.1:9"
    env["HTTP_PROXY"] = "http://127.0.0.1:9"
    env["HTTPS_PROXY"] = "http://127.0.0.1:9"
    env["ALL_PROXY"] = "http://127.0.0.1:9"
    env["no_proxy"] = ""
    env["NO_PROXY"] = ""
    exe = Path(sys.executable).parent / "sigma"
    cmd = [str(exe) if exe.exists() else "sigma", "check", "--fail-on-issues", "--fail-on-error", str(ROOT / "rules")]
    completed = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert completed.returncode == 0, completed.stderr + completed.stdout
