"""Warm the pinned MITRE cache before any test imports pySigma tag data.

sigma check, run as a subprocess by tests/test_gates.py, reads
~/.cache/pysigma and downloads on a miss. Loading the pinned files here fills
that cache without a network connection.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import attack_data  # noqa: E402

attack_data.use_pinned_mitre()
