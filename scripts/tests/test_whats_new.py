"""Tests for whats_new.py CLI script.

Uses the shared base_world.xml fixture from conftest.py and exercises
the script via subprocess to validate CLI behaviour end-to-end.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "whats_new.py"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run(df_root: Path, xml_path: str, *args: str) -> subprocess.CompletedProcess:
    """Run whats_new.py with --xml pointed at a fixture."""
    cmd = [sys.executable, str(SCRIPT), "--xml", xml_path, *args]
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(df_root),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSinceYearFilter:
    """--since-year filters events to the correct range."""

    def test_since_year_101_excludes_earlier(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """Only year 101+ events should appear."""
        r = run(df_root, str(base_world_xml_path), "--since-year", "101")
        assert r.returncode == 0
        out = r.stdout
        # Year 101 and 102 should be present
        assert "Year 101" in out
        assert "Year 102" in out
        # Year 99 and 100 events should NOT appear
        assert "Year 99" not in out
        assert "Year 100" not in out

    def test_since_year_99_includes_all(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """Year 99 should include every event."""
        r = run(df_root, str(base_world_xml_path), "--since-year", "99")
        assert r.returncode == 0
        out = r.stdout
        assert "Year 99" in out
        assert "Year 100" in out
        assert "Year 101" in out
        assert "Year 102" in out


class TestSiteFilter:
    """--site filters events to the named site."""

    def test_site_filter_testfort(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "100", "--site", "testfort",
        )
        assert r.returncode == 0
        # testfort events should be present (artifact created, deaths, etc.)
        assert r.stdout.strip() != ""
        # Should not be empty
        assert "events" in r.stdout.lower()


class TestJsonOutput:
    """--json flag produces valid JSON."""

    def test_json_output_is_valid(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "99", "--json",
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_json_structure_has_seasons_and_categories(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "99", "--json",
        )
        data = json.loads(r.stdout)
        year_entry = data[0]
        assert "year" in year_entry
        assert "seasons" in year_entry
        season = year_entry["seasons"][0]
        assert "season" in season
        assert "categories" in season
        cat = season["categories"][0]
        assert "category" in cat
        assert "count" in cat
        assert "events" in cat


class TestSeasonGrouping:
    """Events are grouped by season based on seconds72."""

    def test_spring_events_grouped(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """Year 99 events (s72 100-300) should all land in Spring."""
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "99", "--json",
        )
        data = json.loads(r.stdout)
        # Year 99 entry
        year99 = [y for y in data if y["year"] == 99][0]
        season_names = [s["season"] for s in year99["seasons"]]
        assert "Spring" in season_names

    def test_battle_events_in_spring(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """Year 101 battle events (s72 ~50000, within 0-100800) → Spring."""
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "101", "--json",
        )
        data = json.loads(r.stdout)
        year101 = [y for y in data if y["year"] == 101][0]
        season_names = [s["season"] for s in year101["seasons"]]
        # s72=50000 falls within Spring (0–100800)
        assert "Spring" in season_names


class TestCategories:
    """Events are sorted into the correct categories."""

    def test_deaths_category(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """hf died event should appear in Deaths."""
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "101", "--json",
        )
        data = json.loads(r.stdout)
        all_cats = {
            cat["category"]
            for y in data for s in y["seasons"] for cat in s["categories"]
        }
        assert "Deaths" in all_cats

    def test_arrivals_category(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """change hf state (settled) events should appear in Arrivals."""
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "99", "--json",
        )
        data = json.loads(r.stdout)
        all_cats = {
            cat["category"]
            for y in data for s in y["seasons"] for cat in s["categories"]
        }
        assert "Arrivals" in all_cats

    def test_artifacts_category(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """artifact created and masterpiece item events → Artifacts."""
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "100", "--json",
        )
        data = json.loads(r.stdout)
        all_cats = {
            cat["category"]
            for y in data for s in y["seasons"] for cat in s["categories"]
        }
        assert "Artifacts" in all_cats

    def test_wars_battles_category(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """hf simple battle event → Wars/Battles."""
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "101", "--json",
        )
        data = json.loads(r.stdout)
        all_cats = {
            cat["category"]
            for y in data for s in y["seasons"] for cat in s["categories"]
        }
        assert "Wars/Battles" in all_cats

    def test_construction_category(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """created site event → Construction."""
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "99", "--json",
        )
        data = json.loads(r.stdout)
        all_cats = {
            cat["category"]
            for y in data for s in y["seasons"] for cat in s["categories"]
        }
        assert "Construction" in all_cats

    def test_trade_category(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """merchant event → Trade."""
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "101", "--json",
        )
        data = json.loads(r.stdout)
        all_cats = {
            cat["category"]
            for y in data for s in y["seasons"] for cat in s["categories"]
        }
        assert "Trade" in all_cats

    def test_diplomacy_category(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        """add hf entity link with position → Diplomacy."""
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "99", "--json",
        )
        data = json.loads(r.stdout)
        all_cats = {
            cat["category"]
            for y in data for s in y["seasons"] for cat in s["categories"]
        }
        assert "Diplomacy" in all_cats


class TestEmptyResults:
    """Graceful handling of no matching events."""

    def test_far_future_year_returns_empty(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        r = run(df_root, str(base_world_xml_path), "--since-year", "999")
        assert r.returncode == 0
        assert "no events" in r.stdout.lower()

    def test_far_future_json_returns_empty_list(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        r = run(
            df_root, str(base_world_xml_path),
            "--since-year", "999", "--json",
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data == []


class TestMissingSinceYear:
    """Missing --since-year should produce an error."""

    def test_missing_since_year_errors(
        self, df_root: Path, base_world_xml_path: Path,
    ) -> None:
        r = run(df_root, str(base_world_xml_path))
        assert r.returncode != 0
        assert "since-year" in r.stderr.lower()
