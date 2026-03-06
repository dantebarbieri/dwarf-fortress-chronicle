"""Tests for site.py.

Each script is invoked as a subprocess from the DF root directory to test
actual CLI behaviour (exit codes, stdout, stderr, JSON output).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure the DF root is on sys.path so conftest constants are importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.tests.conftest import (
    TESTFORT_ID,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run_script(
    df_root: Path,
    script_name: str,
    *args: str,
    xml_path: str,
) -> subprocess.CompletedProcess:
    """Run a filter script from the DF root directory."""
    cmd = [
        sys.executable,
        f"scripts/{script_name}",
        "--xml", xml_path,
        *args,
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(df_root),
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


# ===================================================================
# site.py
# ===================================================================


class TestFilterFortress:
    """Tests for site.py."""

    SCRIPT = "site.py"

    def test_fortress_by_name(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "testfort", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "testfort" in out
        assert "fortress" in out
        assert "10,20" in out  # coords

    def test_fortress_structures(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "testfort", "--structures", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "copper mug" in out
        assert "holy anvil" in out

    def test_fortress_json(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "testfort", "--json", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "overview" in data
        assert data["overview"]["name"].lower() == "testfort"
        assert data["overview"]["id"] == TESTFORT_ID

    def test_fortress_artifacts(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "testfort", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        assert "gleamcutter" in r.stdout.lower()

    def test_fortress_events(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "testfort", "--events", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Event timeline should list events at testfort
        assert "event timeline" in out or "event" in out

    def test_fortress_not_found(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "nonexistent", xml_path=str(sample_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "no site" in combined or "error" in combined


# ===================================================================
# Empty world edge cases
# ===================================================================


class TestEmptyWorldSite:
    """site.py should handle empty XML gracefully."""

    SCRIPT = "site.py"

    def test_site_not_found_empty_world(self, df_root: Path, empty_world_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "anything", xml_path=str(empty_world_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "no site" in combined or "error" in combined or "no " in combined


# ===================================================================
# Site with no structures (empty_world.xml)
# ===================================================================


class TestSiteNoStructures:
    """site.py with empty world — no site to find at all."""

    SCRIPT = "site.py"

    def test_no_site_in_empty_world(self, df_root: Path, empty_world_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "testfort", xml_path=str(empty_world_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "no site" in combined or "error" in combined or "no " in combined

    def test_site_no_structures_dead_figures(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        """gravehall in dead_figures.xml has no structures — should still show overview."""
        r = run_script(df_root, self.SCRIPT, "gravehall", "--structures", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "gravehall" in out
