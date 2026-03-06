"""Tests for civilization, site, and creature scripts.

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
    URIST_ID,
    DORIN_ID,
    SNAGAK_ID,
    DRAGON_ID,
    KIDDO_ID,
    DWARF_CIV_ID,
    SITE_GOV_ID,
    GOBLIN_CIV_ID,
    TESTFORT_ID,
    EVILSPIRE_ID,
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
# creature.py
# ===================================================================


class TestFilterCreature:
    """Tests for creature.py."""

    SCRIPT = "creature.py"

    def test_creature_by_name(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "urist mctest" in out
        assert "dwarf" in out

    def test_creature_partial_match_list(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "mctest", "--list", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Should list both urist and kiddo
        assert "urist mctest" in out
        assert "kiddo mctest" in out

    def test_creature_kills(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "dorin shieldarm", "--kills", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Dorin killed Snagak
        assert "snagak goretooth" in out or "goblin" in out

    def test_creature_events(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", "--events", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "event timeline" in out

    def test_creature_json(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", "--json", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "figure" in data
        assert data["figure"]["id"] == URIST_ID or str(data["figure"]["id"]) == URIST_ID

    def test_creature_dragon(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "blaze firemaw", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "dragon" in out
        assert "blaze firemaw" in out
        # Dragon is an enemy of both civs
        assert "enemy" in out



