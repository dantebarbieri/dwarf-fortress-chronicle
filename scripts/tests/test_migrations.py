"""Tests for migrations.py — migration wave tracker.

Each test invokes the script as a subprocess from the DF root directory to
exercise actual CLI behaviour (exit codes, stdout, stderr, JSON output).
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
    KIDDO_ID,
    TESTFORT_ID,
    DWARF_CIV_ID,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run_script(
    df_root: Path,
    *args: str,
    xml_path: str,
) -> subprocess.CompletedProcess:
    """Run migrations.py from the DF root directory."""
    cmd = [
        sys.executable,
        "scripts/migrations.py",
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
# Tests using base_world.xml (testfort, year 99 has 2 settlers)
# ===================================================================


class TestBasicMigrations:
    """Basic migration listing using the base_world fixture."""

    def test_migration_listing_year_99(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        """Year 99 at testfort should show 2 settlers (Urist + Dorin)."""
        r = run_script(df_root, "testfort", "--year", "99", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "urist mctest" in out
        assert "dorin shieldarm" in out
        assert "2 settlers" in out
        assert "1 wave" in out

    def test_no_migrations_year_100(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        """Year 100 has no new settlers at testfort (only artifacts/masterpieces)."""
        r = run_script(df_root, "testfort", "--year", "100", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "no migrations" in out

    def test_year_range_filter(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        """Year range 99–102 should capture year-99 settlers and year-102 settler."""
        r = run_script(
            df_root, "testfort", "--year-from", "99", "--year-to", "102",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "urist mctest" in out
        assert "dorin shieldarm" in out
        # Kiddo settles in year 102
        assert "kiddo mctest" in out

    def test_site_by_id(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        """Passing a numeric site ID should work."""
        r = run_script(df_root, TESTFORT_ID, "--year", "99", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        assert "urist mctest" in r.stdout.lower()

    def test_unknown_site(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        """An unknown site name should produce a non-zero exit code."""
        r = run_script(df_root, "nonexistent_place", "--year", "99", xml_path=str(sample_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "no site" in combined

    def test_unknown_site_id(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        """An unknown numeric site ID should produce a non-zero exit code."""
        r = run_script(df_root, "99999", "--year", "99", xml_path=str(sample_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "no site" in combined

    def test_missing_year_arg(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        """Omitting year filters should produce an error."""
        r = run_script(df_root, "testfort", xml_path=str(sample_xml_path))
        assert r.returncode != 0


# ===================================================================
# JSON output
# ===================================================================


class TestJsonOutput:
    """JSON mode should produce valid, structured output."""

    def test_json_valid_and_structured(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        r = run_script(
            df_root, "testfort", "--year", "99", "--json",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["site_id"] == TESTFORT_ID
        assert data["total_settlers"] == 2
        assert data["total_waves"] == 1
        assert len(data["waves"]) == 1

    def test_json_settler_fields(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        """Each settler dict should contain expected profile fields."""
        r = run_script(
            df_root, "testfort", "--year", "99", "--json",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        settler = data["waves"][0]["settlers"][0]
        for key in ("hf_id", "name", "race", "caste", "age", "profession",
                     "skills", "family", "entities"):
            assert key in settler, f"Missing key: {key}"

    def test_json_empty_result(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        """Year with no migrations should still produce valid JSON."""
        r = run_script(
            df_root, "testfort", "--year", "100", "--json",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["total_settlers"] == 0
        assert data["waves"] == []


# ===================================================================
# Profile correctness
# ===================================================================


class TestProfileInfo:
    """Verify that individual settler profiles contain correct data."""

    def test_urist_profile(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        """Urist's profile should show correct name, race, age, skills, family."""
        r = run_script(
            df_root, "testfort", "--year", "99", "--json",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        settlers = data["waves"][0]["settlers"]

        urist = next(s for s in settlers if s["hf_id"] == URIST_ID)
        assert urist["name"] == "Urist Mctest"
        assert urist["race"] == "DWARF"
        assert urist["caste"] == "male"
        assert urist["age"] == 59  # born year 40, settled year 99
        assert urist["profession"] == "Planter"

        # Top skills should include Plant (highest IP)
        skill_names = [sk["skill"] for sk in urist["skills"]]
        assert "Plant" in skill_names

        # Family should include spouse Dorin
        family_relations = {f["relation"]: f["name"] for f in urist["family"]}
        assert "spouse" in family_relations
        assert "dorin shieldarm" in family_relations["spouse"].lower()

        # Entity memberships should include the dwarf civ
        ent_ids = [e["entity_id"] for e in urist["entities"]]
        assert DWARF_CIV_ID in ent_ids

    def test_dorin_profile(
        self, df_root: Path, sample_xml_path: Path,
    ) -> None:
        """Dorin's profile should show correct age, skills, and family."""
        r = run_script(
            df_root, "testfort", "--year", "99", "--json",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        settlers = data["waves"][0]["settlers"]

        dorin = next(s for s in settlers if s["hf_id"] == DORIN_ID)
        assert dorin["name"] == "Dorin Shieldarm"
        assert dorin["age"] == 61  # born year 38, settled year 99
        assert dorin["profession"] == "Hammerman"

        # Top 3 skills (Hammer 18700, Dodging 8200, Shield 5700)
        assert len(dorin["skills"]) == 3
        assert dorin["skills"][0]["skill"] == "Hammer"


# ===================================================================
# Migration waves fixture (multiple waves)
# ===================================================================


class TestMigrationWaves:
    """Tests using the migration_waves.xml fixture with multiple waves."""

    def test_year_100_two_waves(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """Year 100 at newhome should show 2 waves (3 founders + 2 autumn)."""
        r = run_script(
            df_root, "newhome", "--year", "100",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "wave 1" in out
        assert "wave 2" in out
        assert "5 settlers" in out
        assert "2 waves" in out

    def test_year_101_single_wave(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """Year 101 at newhome should show 1 wave with 4 settlers."""
        r = run_script(
            df_root, "newhome", "--year", "101",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "wave 1" in out
        assert "4 settlers" in out
        assert "1 wave" in out

    def test_full_range_three_waves(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """Year range 100–101 should show all 3 waves and 9 total settlers."""
        r = run_script(
            df_root, "newhome", "--year-from", "100", "--year-to", "101",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "wave 1" in out
        assert "wave 2" in out
        assert "wave 3" in out
        assert "9 settlers" in out
        assert "3 waves" in out

    def test_json_multiple_waves(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """JSON output should correctly structure multiple waves."""
        r = run_script(
            df_root, "newhome", "--year-from", "100", "--year-to", "101", "--json",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["total_waves"] == 3
        assert data["total_settlers"] == 9
        # Wave 1 should have 3 settlers
        assert len(data["waves"][0]["settlers"]) == 3
        # Wave 2 should have 2 settlers
        assert len(data["waves"][1]["settlers"]) == 2
        # Wave 3 should have 4 settlers
        assert len(data["waves"][2]["settlers"]) == 4

    def test_wave_settlers_have_skills(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """Settlers in migration_waves fixture should have skill data."""
        r = run_script(
            df_root, "newhome", "--year", "100", "--json",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        # First wave, first settler (Zon Clearchannel — MINER)
        zon = data["waves"][0]["settlers"][0]
        assert zon["name"] == "Zon Clearchannel"
        assert len(zon["skills"]) >= 1
        assert zon["skills"][0]["skill"] == "Mining"

    def test_wave_family_links(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """Rigoth Ironquill (wave 2) should show child link to Ducim."""
        r = run_script(
            df_root, "newhome", "--year", "100", "--json",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        # Wave 2, first settler: Rigoth
        rigoth = data["waves"][1]["settlers"][0]
        assert rigoth["name"] == "Rigoth Ironquill"
        child_names = [f["name"].lower() for f in rigoth["family"] if f["relation"] == "child"]
        assert any("ducim" in n for n in child_names)

    def test_site_by_id_migration_waves(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """Using numeric site ID 1000 should work."""
        r = run_script(
            df_root, "1000", "--year", "100",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0, r.stderr
        assert "5 settlers" in r.stdout.lower()
