"""Tests for civilization.py.

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
    DWARF_CIV_ID,
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
# civilization.py
# ===================================================================


class TestFilterCivilization:
    """Tests for civilization.py."""

    SCRIPT = "civilization.py"

    def test_civ_by_name(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "guilds of testing", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "guilds of testing" in out
        # Population section should list members
        assert "population" in out or "member" in out

    def test_civ_by_id(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, DWARF_CIV_ID, xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        assert "guilds of testing" in r.stdout.lower()

    def test_civ_not_found(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "nonexistent", xml_path=str(sample_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "error" in combined or "no entity" in combined or "no " in combined

    def test_civ_json(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "guilds of testing", "--json", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "entity" in data
        assert "population" in data
        assert data["population"]["total"] > 0

    def test_civ_members_flag(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "guilds of testing", "--members", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Full member list should contain known dwarf names
        assert "urist mctest" in out or "dorin shieldarm" in out

    def test_civ_wars_flag(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "guilds of testing", "--wars", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "test war" in out

    def test_civ_year_filter(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "guilds of testing", "--year", "100", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Year-100 events section should appear
        assert "event" in out
        # Year-101 specific events (like hf died) should NOT appear
        assert "hf died" not in out


# ===================================================================
# Empty world edge cases
# ===================================================================


class TestEmptyWorldCivilization:
    """civilization.py should handle empty XML gracefully."""

    SCRIPT = "civilization.py"

    def test_civ_not_found_empty_world(self, df_root: Path, empty_world_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "anything", xml_path=str(empty_world_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "no entity" in combined or "error" in combined or "no " in combined


# ===================================================================
# Civilization with no members (empty_world.xml)
# ===================================================================


class TestCivNoMembers:
    """civilization.py with empty world — no entity to find at all."""

    SCRIPT = "civilization.py"

    def test_no_entity_in_empty_world(self, df_root: Path, empty_world_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "guilds", xml_path=str(empty_world_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "no entity" in combined or "error" in combined or "no " in combined
