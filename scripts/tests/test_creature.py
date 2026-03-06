"""Tests for creature.py.

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


# ===================================================================
# Empty world edge cases
# ===================================================================


class TestEmptyWorldCreature:
    """creature.py should handle empty XML gracefully."""

    SCRIPT = "creature.py"

    def test_creature_not_found_empty_world(self, df_root: Path, empty_world_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "anything", xml_path=str(empty_world_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "no " in combined or "error" in combined


# ===================================================================
# Dead figures: creature.py should show death info
# ===================================================================


class TestDeadFigureCreature:
    """creature.py should display death info for dead figures."""

    SCRIPT = "creature.py"

    def test_dead_figure_struck(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "ingiz axefall", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "ingiz axefall" in out
        assert "95" in out  # death year

    def test_dead_figure_old_age(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "erush lonelypick", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "erush lonelypick" in out
        assert "80" in out  # death year

    def test_dead_figure_drowned(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "bomrek wetlungs", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "bomrek wetlungs" in out
        assert "85" in out  # death year
