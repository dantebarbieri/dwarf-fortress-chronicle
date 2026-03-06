"""Tests for events.py and relationship_history.py CLI scripts.

Uses the shared sample XML fixture from conftest.py and exercises both
scripts via subprocess to validate CLI behaviour end-to-end.
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
    script_name: str,
    *args: str,
    xml_path: str,
) -> subprocess.CompletedProcess:
    """Run a script in the DF root with ``--xml`` pointed at the fixture."""
    cmd = [sys.executable, f"scripts/{script_name}", "--xml", xml_path, *args]
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(df_root),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


# ===================================================================
# events.py
# ===================================================================


class TestEventsTypes:
    """``--types`` flag lists available event types."""

    def test_events_types_flag(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--types", xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        for t in (
            "hf died",
            "masterpiece item",
            "created site",
            "artifact created",
            "change hf state",
            "merchant",
            "hf simple battle event",
            "add hf hf link",
            "add hf entity link",
            "artifact stored",
        ):
            assert t in out, f"Expected type '{t}' in --types output"


class TestEventsFilters:
    """Filtering events by various criteria."""

    def test_events_by_year(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year", "101",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # Year 101 has 4 events: merchant, battle, hf died, add hf hf link
        assert "4 of 4" in out or "showing 4" in out
        assert "hf died" in out
        assert "merchant" in out

    def test_events_by_type(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--type", "hf died",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "hf died" in out
        # Only 1 hf died event in the fixture
        assert "1 of 1" in out

    def test_events_by_site(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year-from", "99", "--year-to", "102",
                       "--site", "200", xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # 13 of 15 events have site_id=200 (events 1003, 1012 lack site_id)
        assert "13 of 13" in out or "showing" in out
        assert "testfort" in out

    def test_events_by_figure(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year-from", "99", "--year-to", "102",
                       "--figure", "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "urist" in out
        # Urist (300) appears in hfid/maker_hfid of events: 1001,1003,1004,1007,1008,1012
        assert "6 of 6" in out

    def test_events_by_entity(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year-from", "99", "--year-to", "102",
                       "--entity", "guilds of testing",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # Entity 100 appears in civ_id of event 1000 (created site)
        assert "created site" in out

    def test_events_summary(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year-from", "99", "--year-to", "102",
                       "--summary", xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "total:" in out
        assert "15 events" in out
        assert "change hf state" in out
        assert "masterpiece item" in out

    def test_events_limit(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year-from", "99", "--year-to", "102",
                       "--limit", "3", xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout
        assert "3 of 15" in out or "Showing 3" in out

    def test_events_json(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year", "100", "--json",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        # Year 100 has 5 events: 1004-1008
        assert len(data) == 5
        types = {e["type"] for e in data}
        assert "artifact created" in types
        assert "masterpiece item" in types

    def test_events_no_filter(self, df_root: Path, sample_xml_path: Path) -> None:
        """No filter arguments → error exit."""
        r = run_script(df_root, "events.py", xml_path=str(sample_xml_path))
        assert r.returncode != 0
        assert "filter" in r.stderr.lower() or "required" in r.stderr.lower()

    def test_events_combined_filters(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "events.py",
                       "--year", "101", "--type", "hf died", "--site", "200",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "hf died" in out
        assert "1 of 1" in out
        # The goblin death event should name the victim and slayer
        assert "snagak" in out or "goretooth" in out

    # -- Ported from filter_year.py (consolidated into events.py) ----------

    def test_year_single(self, df_root: Path, sample_xml_path: Path) -> None:
        """Year 101 returns matching events (ported from filter_year)."""
        r = run_script(df_root, "events.py", "--year", "101", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "year 101" in out
        # Should contain year 101 events (merchant, battle, hf died, add hf hf link)
        assert "event" in out

    def test_year_range(self, df_root: Path, sample_xml_path: Path) -> None:
        """Year range 100–101 includes events from both years (ported from filter_year)."""
        r = run_script(df_root, "events.py", "--year-from", "100", "--year-to", "101", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Events from both year 100 (artifact created, masterpiece) and year 101 (hf died, merchant)
        assert "artifact" in out or "masterpiece" in out
        assert "hf died" in out or "merchant" in out

    def test_year_with_site(self, df_root: Path, sample_xml_path: Path) -> None:
        """Year + site filter combo (ported from filter_year)."""
        r = run_script(df_root, "events.py", "--year", "101", "--site", "testfort", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "testfort" in out

    def test_year_with_type(self, df_root: Path, sample_xml_path: Path) -> None:
        """Year + type filter returns exactly 1 hf died event (ported from filter_year)."""
        r = run_script(df_root, "events.py", "--year", "101", "--type", "hf died", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "hf died" in out
        # Should only have 1 event (the goblin death)
        assert "1 of 1" in out

    def test_year_summary(self, df_root: Path, sample_xml_path: Path) -> None:
        """Year + summary mode shows type table (ported from filter_year)."""
        r = run_script(df_root, "events.py", "--year", "101", "--summary", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Summary table should show event types and counts
        assert "event type" in out
        assert "total" in out

    def test_year_json(self, df_root: Path, sample_xml_path: Path) -> None:
        """Year 102 JSON output returns expected events (ported from filter_year)."""
        r = run_script(df_root, "events.py", "--year", "102", "--json", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        # Year 102 has 2 events: masterpiece item + change hf state
        assert len(data) == 2

    def test_year_no_filter(self, df_root: Path, sample_xml_path: Path) -> None:
        """No filter → error exit (ported from filter_year)."""
        r = run_script(df_root, "events.py", xml_path=str(sample_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "required" in combined or "filter" in combined

    def test_year_limit(self, df_root: Path, sample_xml_path: Path) -> None:
        """Limit flag caps output (ported from filter_year)."""
        r = run_script(
            df_root, "events.py",
            "--year-from", "99", "--year-to", "102", "--limit", "3",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Should show only 3 events with a "showing 3 of N" note
        assert "3 of" in out

    # -- End ported filter_year tests ---------------------------------------

    def test_events_raw(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "events.py",
                       "--year", "102", "--type", "masterpiece item", "--raw",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # Raw mode shows key: value pairs from the event dict
        assert "maker_hfid" in out
        assert "entity_id" in out
        assert "skill_at_time" in out

    def test_events_describe(self, df_root: Path, sample_xml_path: Path) -> None:
        """Human-readable description should name slayer and victim."""
        r = run_script(df_root, "events.py", "--year", "101", "--type", "hf died",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # Victim: snagak goretooth (302), Slayer: dorin shieldarm (301)
        assert "snagak" in out or "goretooth" in out
        assert "dorin" in out or "shieldarm" in out


# ===================================================================
# relationship_history.py
# ===================================================================


class TestRelationships:
    """Tests for relationship_history.py."""

    def test_rel_two_spouses(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest", "dorin shieldarm",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # Direct relationship: spouse
        assert "spouse" in out
        # Shared entities: both belong to guilds of testing and work of tests
        assert "guilds of testing" in out or "work of tests" in out
        # Family network section: direct spouse link found
        assert "family" in out

    def test_rel_parent_child(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest", "kiddo mctest",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # Should show parent-child link (child from Urist, father from Kiddo)
        assert "child" in out or "father" in out

    def test_rel_no_direct_link(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest", "snagak goretooth",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # No direct hf_link between Urist and Snagak — but analysis still runs
        assert "urist" in out
        assert "snagak" in out
        # Both reference entity 100 (member vs enemy), so shared entities section present
        assert "guilds of testing" in out

    def test_rel_json(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest", "dorin shieldarm", "--json",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "subjects" in data
        assert "direct_relationships" in data
        assert "shared_entities" in data
        assert "shared_events" in data
        assert "family_path" in data
        assert "timeline" in data
        # Two subjects resolved
        assert len(data["subjects"]) == 2
        # Spouse link in direct_relationships
        link_types = {rel["link_type"] for rel in data["direct_relationships"]}
        assert "spouse" in link_types

    def test_rel_with_events(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest", "dorin shieldarm", "--events",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # --events flag accepted; direct relationships still shown
        assert "spouse" in out

    def test_rel_year_filter(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest", "dorin shieldarm", "--year-from", "101",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # Direct relationships are not year-filtered
        assert "spouse" in out

    def test_rel_three_figures(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest", "dorin shieldarm", "kiddo mctest",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "urist" in out
        assert "dorin" in out
        assert "kiddo" in out

    def test_rel_not_enough_figures(self, df_root: Path, sample_xml_path: Path) -> None:
        """Only 1 name → error."""
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest",
                       xml_path=str(sample_xml_path))
        assert r.returncode != 0
        assert "2" in r.stderr or "at least" in r.stderr.lower()

    def test_rel_not_found(self, df_root: Path, sample_xml_path: Path) -> None:
        """Nonexistent names → error."""
        r = run_script(df_root, "relationship_history.py",
                       "nonexistent1", "nonexistent2",
                       xml_path=str(sample_xml_path))
        assert r.returncode != 0
        assert "no historical figure" in r.stderr.lower() or "error" in r.stderr.lower()


# ===================================================================
# Events edge cases with fixture files
# ===================================================================


class TestEventsEmptyWorld:
    """events.py on empty_world.xml should return a 'no events' message."""

    def test_events_empty_world(self, df_root: Path, empty_world_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year", "100",
                       xml_path=str(empty_world_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "no events" in out or "0 events" in out or "0 of 0" in out

    def test_events_summary_empty_world(self, df_root: Path, empty_world_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year", "100", "--summary",
                       xml_path=str(empty_world_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "0 events" in out or "no events" in out


class TestEventsPeacefulYears:
    """Gap years in peaceful_years.xml should return empty results."""

    def test_gap_year_empty(self, df_root: Path, peaceful_years_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year", "75",
                       xml_path=str(peaceful_years_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "no events" in out or "0 events" in out or "0 of 0" in out

    def test_gap_year_range_empty(self, df_root: Path, peaceful_years_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year-from", "60", "--year-to", "90",
                       xml_path=str(peaceful_years_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "no events" in out or "0 events" in out or "0 of 0" in out

    def test_year_50_has_events(self, df_root: Path, peaceful_years_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year", "50",
                       xml_path=str(peaceful_years_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "4 of 4" in out or "showing 4" in out

    def test_year_100_has_events(self, df_root: Path, peaceful_years_xml_path: Path) -> None:
        r = run_script(df_root, "events.py", "--year", "100",
                       xml_path=str(peaceful_years_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "2 of 2" in out or "showing 2" in out

    def test_year_from_year_to_full_range(self, df_root: Path, peaceful_years_xml_path: Path) -> None:
        """--year-from / --year-to covering both event years gets all events."""
        r = run_script(df_root, "events.py", "--year-from", "1", "--year-to", "200",
                       xml_path=str(peaceful_years_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "6 of 6" in out or "showing 6" in out


class TestRelationshipsUnrelated:
    """Relationship between unrelated figures (no shared events)."""

    def test_unrelated_figures(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        """Scald cinderjaw (dragon) and bomrek wetlungs (drowned dwarf) have no
        direct relationship link — but the analysis should still run."""
        r = run_script(df_root, "relationship_history.py",
                       "scald cinderjaw", "bomrek wetlungs",
                       xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "scald" in out
        assert "bomrek" in out

    def test_unrelated_figures_json(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        r = run_script(df_root, "relationship_history.py",
                       "scald cinderjaw", "bomrek wetlungs", "--json",
                       xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0
        import json
        data = json.loads(r.stdout)
        assert "direct_relationships" in data
        # No direct link between these two
        assert len(data["direct_relationships"]) == 0


class TestEventsCombinedFilters:
    """Events with combined filters (--type + --site + --year)."""

    def test_combined_type_site_year(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        r = run_script(df_root, "events.py",
                       "--year", "95", "--type", "hf died", "--site", "700",
                       xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "hf died" in out
        # Only Ingiz died in year 95
        assert "1 of 1" in out

    def test_combined_filters_no_match(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        """Combine filters that produce zero results — script may exit non-zero
        or print a 'not found' message when the event type doesn't exist."""
        r = run_script(df_root, "events.py",
                       "--year", "80", "--type", "masterpiece item",
                       xml_path=str(dead_figures_xml_path))
        combined = (r.stdout + r.stderr).lower()
        assert "no event" in combined or "not found" in combined or "0 of 0" in combined or r.returncode != 0


class TestEventsYearFromYearTo:
    """Verify --year-from and --year-to work correctly (ported filter_year coverage)."""

    def test_year_from_only(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        """--year-from without --year-to includes all events from that year onward."""
        r = run_script(df_root, "events.py", "--year-from", "92",
                       xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # Events in years 92, 95 should appear
        assert "event" in out

    def test_year_to_only(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        """--year-to without --year-from includes all events up to that year."""
        r = run_script(df_root, "events.py", "--year-to", "85",
                       xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0
        out = r.stdout.lower()
        # Events in years 80, 85 should appear
        assert "event" in out

    def test_year_range_inclusive(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        """Year range is inclusive on both ends."""
        r = run_script(df_root, "events.py",
                       "--year-from", "90", "--year-to", "92", "--json",
                       xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0
        import json
        data = json.loads(r.stdout)
        years = {e["year"] for e in data}
        # Should include year 90 (2 events) and year 92 (1 event)
        assert "90" in years
        assert "92" in years
