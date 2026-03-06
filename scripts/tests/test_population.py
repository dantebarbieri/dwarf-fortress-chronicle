"""Tests for population.py — population census tracker.

Uses base_world.xml and migration_waves.xml fixtures.  Exercises the
CLI end-to-end via subprocess, matching the test patterns used by
existing test modules.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run_script(
    df_root: Path,
    *args: str,
    xml_path: str,
) -> subprocess.CompletedProcess:
    """Run population.py in the DF root with ``--xml`` pointed at a fixture."""
    cmd = [sys.executable, "scripts/population.py", "--xml", xml_path, *args]
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(df_root),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


# ===================================================================
# base_world.xml tests  (testfort: 2 arrive yr99, 1 dies yr101, 1 arrives yr102)
# ===================================================================


class TestBasicPopulation:
    """Core population tracking against base_world.xml."""

    def test_basic_population_tracking(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """2 arrive in year 99, goblin dies in 101, 1 arrives in 102."""
        r = run_script(df_root, "testfort", xml_path=str(base_world_xml_path))
        assert r.returncode == 0
        out = r.stdout

        # Year 99: 2 arrivals
        assert "Year 99:" in out
        assert "Urist Mctest" in out
        assert "Dorin Shieldarm" in out

        # Year 102: 1 more arrival
        assert "Year 102:" in out
        assert "Kiddo Mctest" in out

        # Final population should be 3 (the goblin death doesn't subtract
        # from population counted by settlements — Snagak never settled)
        # Actually: 2 settled in yr99, goblin died yr101 but never settled,
        # 1 settled yr102 → 3 current.
        assert "Current population: 3" in out

    def test_year_filtering(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """Year range filtering limits output."""
        r = run_script(
            df_root, "testfort",
            "--year-from", "100", "--year-to", "101",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0
        out = r.stdout

        # Should NOT show year 99 or 102 entries
        assert "Year 99:" not in out
        assert "Year 102:" not in out

        # But should still count the pre-window arrivals for population
        # (2 arrived before year 100, so end of year 100 = 2)
        assert "End:     2" in out

    def test_by_race(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """--by-race shows race breakdown."""
        r = run_script(
            df_root, "testfort", "--by-race",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0
        out = r.stdout
        assert "DWARF: 3" in out

    def test_json_output(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """--json produces valid JSON with expected structure."""
        r = run_script(
            df_root, "testfort", "--json",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["site_name"] == "Testfort"
        assert data["current_population"] == 3
        assert isinstance(data["years"], list)
        assert len(data["years"]) > 0
        assert data["years"][0]["year"] == 99

    def test_json_by_race(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """--json --by-race includes race breakdown in JSON."""
        r = run_script(
            df_root, "testfort", "--json", "--by-race",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "by_race" in data
        assert data["by_race"]["DWARF"] == 3


class TestUnknownSite:
    """Error handling for unknown sites."""

    def test_unknown_site_error(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """Unknown site name produces an error."""
        r = run_script(
            df_root, "nosuchfort",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode != 0
        assert "no site" in r.stderr.lower()

    def test_unknown_site_id_still_runs(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """A numeric ID that doesn't match any site produces empty output."""
        r = run_script(
            df_root, "99999",
            xml_path=str(base_world_xml_path),
        )
        # Numeric IDs are accepted but will show zero population
        assert r.returncode == 0
        assert "Current population: 0" in r.stdout


class TestEmptySite:
    """Site with no population events."""

    def test_empty_site(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """evilspire has no settlement events — population should be 0."""
        r = run_script(
            df_root, "evilspire",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0
        assert "Current population: 0" in r.stdout


# ===================================================================
# dead_figures.xml tests  (gravehall: deaths but no settlements)
# ===================================================================


class TestSiteWithDeaths:
    """Population tracking at a site with deaths (dead_figures.xml).

    dead_figures.xml has gravehall (site 700) with several deaths but
    NO settlement events.  This tests that deaths alone don't produce
    negative population.  We also test that if we add settlements before
    the deaths, the subtraction works correctly — but with the current
    fixture, population stays at 0 since nobody settled.
    """

    def test_deaths_without_settlements(
        self, df_root: Path, dead_figures_xml_path: Path,
    ) -> None:
        """Deaths at gravehall without prior settlements → 0 population.

        Since nobody settled at gravehall, deaths of non-residents are
        not counted toward population changes.
        """
        r = run_script(
            df_root, "gravehall",
            xml_path=str(dead_figures_xml_path),
        )
        assert r.returncode == 0
        out = r.stdout
        assert "Current population: 0" in out

    def test_deaths_json(
        self, df_root: Path, dead_figures_xml_path: Path,
    ) -> None:
        """JSON output for site with deaths is valid."""
        r = run_script(
            df_root, "gravehall", "--json",
            xml_path=str(dead_figures_xml_path),
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["site_name"] == "Gravehall"
        # Deaths without settlements means negative or zero
        assert isinstance(data["current_population"], int)


# ===================================================================
# migration_waves.xml tests  (newhome: 3 in yr100, 2 more yr100, 4 in yr101)
# ===================================================================


class TestMigrationWaves:
    """Population tracking with multiple migration waves."""

    def test_migration_total(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """newhome: 5 in year 100 + 4 in year 101 = 9 total."""
        r = run_script(
            df_root, "newhome",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0
        out = r.stdout
        assert "Current population: 9" in out

    def test_migration_year_100(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """Year 100 should show 5 arrivals."""
        r = run_script(
            df_root, "newhome", "--year", "100",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0
        out = r.stdout
        assert "Arrived: 5" in out
        assert "End:     5" in out

    def test_migration_year_101(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """Year 101 should show 4 arrivals, end population 9."""
        r = run_script(
            df_root, "newhome", "--year", "101",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0
        out = r.stdout
        assert "Arrived: 4" in out
        assert "End:     9" in out

    def test_migration_by_race(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """All migrants at newhome are dwarves."""
        r = run_script(
            df_root, "newhome", "--by-race",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0
        assert "DWARF: 9" in out if (out := r.stdout) else False

    def test_migration_json(
        self, df_root: Path, migration_waves_xml_path: Path,
    ) -> None:
        """JSON output for migration waves is valid and correct."""
        r = run_script(
            df_root, "newhome", "--json",
            xml_path=str(migration_waves_xml_path),
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["current_population"] == 9
        assert len(data["years"]) == 2  # years 100 and 101
        assert data["years"][0]["arrived"] == 5
        assert data["years"][1]["arrived"] == 4
