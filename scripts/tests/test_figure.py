"""Tests for figure.py — historical figure profiles.

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

from scripts.tests.conftest import URIST_ID


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run_script(
    df_root: Path,
    script_name: str,
    *args: str,
    xml_path: str,
) -> subprocess.CompletedProcess:
    """Run a script from the DF root directory."""
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
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


# ===================================================================
# figure.py
# ===================================================================


class TestDwarf:
    """Tests for figure.py."""

    SCRIPT = "figure.py"

    def test_dwarf_profile(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        out_lower = out.lower()
        assert "urist mctest" in out_lower
        assert "dwarf" in out_lower
        assert "male" in out_lower
        assert "40" in out  # birth year
        assert "PLANTER" in out

    def test_dwarf_entity_memberships(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "guilds of testing" in out
        assert "work of tests" in out

    def test_dwarf_positions(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        # Position at entity 101 (The Work Of Tests)
        assert "101" in out or "Work Of Tests" in out

    def test_dwarf_skills(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        assert "PLANT" in out
        assert "Expert" in out

    def test_dwarf_family(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "dorin shieldarm" in out
        # Deity link (blaze firemaw) appears in the family section
        assert "deity" in out

    def test_dwarf_json(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", "--json", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "identity" in data
        assert "top_skills" in data
        assert "family" in data
        assert data["identity"]["name"].lower() == "urist mctest"

    def test_dwarf_ambiguous(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "mctest", xml_path=str(sample_xml_path))
        assert r.returncode != 0
        # Should list both matching figures
        combined = (r.stdout + r.stderr).lower()
        assert "urist mctest" in combined or "2" in combined

    def test_dwarf_not_found(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "nonexistent", xml_path=str(sample_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "no " in combined or "error" in combined

    def test_dwarf_by_id(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, URIST_ID, xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "urist mctest" in out
        assert "dwarf" in out


# ===================================================================
# Dead figure profile (dead_figures.xml)
# ===================================================================


class TestDeadFigureProfile:
    """figure.py should show death year and cause for dead figures."""

    SCRIPT = "figure.py"

    def test_dead_figure_shows_death_year(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "ingiz axefall", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        assert "95" in out  # death year
        assert "ingiz" in out.lower()

    def test_dead_figure_old_age(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "erush lonelypick", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        assert "80" in out  # death year
        assert "erush" in out.lower()

    def test_dead_megabeast_victim(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "asmel brightiron", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        assert "90" in out  # death year

    def test_dead_figure_json_has_death_year(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "ingiz axefall", "--json", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["identity"]["death_year"] == "95"


# ===================================================================
# figure.py with --race filter
# ===================================================================


class TestFigureRaceFilter:
    """figure.py --race should filter matches by race."""

    SCRIPT = "figure.py"

    def test_race_filter_dwarf(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        """Searching for a broad term with --race DWARF should only show dwarves."""
        r = run_script(df_root, self.SCRIPT, "goden hammerthane", "--race", "DWARF", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "dwarf" in out
        assert "goden" in out

    def test_race_filter_dragon(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "scald cinderjaw", "--race", "DRAGON", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "dragon" in out
        assert "scald" in out

    def test_race_filter_no_match(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        """Searching for a dwarf name with --race GOBLIN should fail."""
        r = run_script(df_root, self.SCRIPT, "goden hammerthane", "--race", "GOBLIN", xml_path=str(dead_figures_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "no " in combined or "error" in combined
