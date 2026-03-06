"""Tests for interactions.py — entity-to-entity interaction log."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import (  # noqa: E402
    DWARF_CIV_ID,
    GOBLIN_CIV_ID,
    SITE_GOV_ID,
)


def run_script(
    df_root: Path, script_name: str, *args: str, xml_path: str
) -> subprocess.CompletedProcess:
    """Run a script as a subprocess and return the result."""
    cmd = [sys.executable, f"scripts/{script_name}", *args, "--xml", xml_path]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(df_root),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


SCRIPT = "interactions.py"


# ===================================================================
# base_world.xml — guilds of testing vs dark horde
# ===================================================================


class TestBaseWorldWarAndBattle:
    """Guilds of testing vs dark horde should show war and battle."""

    def test_shows_war(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "the test war" in out

    def test_shows_battle(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "siege of testfort" in out

    def test_shows_both_entity_names(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "guilds of testing" in out
        assert "dark horde" in out

    def test_by_id(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            DWARF_CIV_ID, GOBLIN_CIV_ID,
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "the test war" in out
        assert "siege of testfort" in out

    def test_interaction_count(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        # Should have at least 2 interactions (war + battle)
        assert "interaction(s) found" in r.stdout.lower()


# ===================================================================
# Year filtering
# ===================================================================


class TestYearFiltering:
    def test_year_filter_includes(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            "--year", "101",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "the test war" in out
        assert "siege of testfort" in out

    def test_year_filter_excludes(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            "--year", "50",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "0 interaction(s) found" in out

    def test_year_from(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            "--year-from", "100",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "the test war" in out

    def test_year_to(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            "--year-to", "100",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        # War starts year 101, should be excluded
        out = r.stdout.lower()
        assert "0 interaction(s) found" in out


# ===================================================================
# JSON output
# ===================================================================


class TestJsonOutput:
    def test_json_valid(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            "--json",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        data = json.loads(r.stdout)
        assert isinstance(data, dict)

    def test_json_structure(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            "--json",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        data = json.loads(r.stdout)
        assert "entity_1" in data
        assert "entity_2" in data
        assert "interactions" in data
        assert "summary" in data
        assert data["summary"]["total"] >= 2

    def test_json_has_wars(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            "--json",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        data = json.loads(r.stdout)
        wars = data["interactions"]["wars"]
        assert len(wars) >= 1
        assert "the test war" in wars[0]["name"].lower()

    def test_json_has_battles(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            "--json",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        data = json.loads(r.stdout)
        battles = data["interactions"]["battles"]
        assert len(battles) >= 1
        assert "siege of testfort" in battles[0]["name"].lower()


# ===================================================================
# Category filtering
# ===================================================================


class TestCategoryFiltering:
    def test_filter_wars_only(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            "--category", "wars",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "the test war" in out
        assert "siege of testfort" not in out

    def test_filter_battles_only(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "dark horde",
            "--category", "battles",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "siege of testfort" in out
        assert "=== wars ===" not in out


# ===================================================================
# No interactions
# ===================================================================


class TestNoInteractions:
    def test_no_interactions_graceful(self, df_root: Path, base_world_xml_path: Path) -> None:
        """Dwarves and humans in multi_war have no shared interactions."""
        r = run_script(
            df_root, SCRIPT,
            DWARF_CIV_ID, GOBLIN_CIV_ID,
            "--category", "trade",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "0 interaction(s) found" in out


# ===================================================================
# Invalid entity
# ===================================================================


class TestInvalidEntity:
    def test_invalid_first_entity(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "nonexistent civilization", "dark horde",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode != 0
        assert "error" in r.stderr.lower() or "no entity" in r.stderr.lower()

    def test_invalid_second_entity(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "nonexistent civilization",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode != 0
        assert "error" in r.stderr.lower() or "no entity" in r.stderr.lower()


# ===================================================================
# Same entity
# ===================================================================


class TestSameEntity:
    def test_same_entity_error(self, df_root: Path, base_world_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "guilds of testing", "guilds of testing",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode != 0
        assert "same entity" in r.stderr.lower()


# ===================================================================
# multi_war.xml — multiple conflicts
# ===================================================================


class TestMultiWar:
    def test_dwarves_vs_goblins(self, df_root: Path, multi_war_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "shields of order", "dark fangs",
            xml_path=str(multi_war_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "war of iron and fang" in out
        assert "assault on shieldvault" in out
        assert "raid on hatespike" in out

    def test_goblins_vs_humans(self, df_root: Path, multi_war_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "dark fangs", "crossroads alliance",
            xml_path=str(multi_war_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "crossroads conflict" in out
        assert "battle of crossroads" in out

    def test_dwarves_vs_humans_empty(self, df_root: Path, multi_war_xml_path: Path) -> None:
        """Dwarves and humans have no direct war/battle."""
        r = run_script(
            df_root, SCRIPT,
            "shields of order", "crossroads alliance",
            xml_path=str(multi_war_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "0 interaction(s) found" in out

    def test_multi_war_json(self, df_root: Path, multi_war_xml_path: Path) -> None:
        r = run_script(
            df_root, SCRIPT,
            "shields of order", "dark fangs",
            "--json",
            xml_path=str(multi_war_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        data = json.loads(r.stdout)
        assert data["summary"]["wars"] >= 1
        assert data["summary"]["battles"] >= 2
        assert data["summary"]["total"] >= 3

    def test_multi_war_year_filter(self, df_root: Path, multi_war_xml_path: Path) -> None:
        """Filter to year 102 should catch the second battle only."""
        r = run_script(
            df_root, SCRIPT,
            "shields of order", "dark fangs",
            "--year", "102",
            xml_path=str(multi_war_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "raid on hatespike" in out
        # War starts year 100 and battle 1 is year 100 — both excluded
        assert "assault on shieldvault" not in out
