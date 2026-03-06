"""Tests for relationship_history.py CLI script.

Uses the shared sample XML fixture from conftest.py and exercises the
script via subprocess to validate CLI behaviour end-to-end.
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

    def test_rel_include_indirect_flag(self, df_root: Path, sample_xml_path: Path) -> None:
        """--include-indirect runs cleanly and produces output."""
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest", "dorin shieldarm", "--include-indirect",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        assert r.stdout.strip()

    def test_rel_include_indirect_json(self, df_root: Path, sample_xml_path: Path) -> None:
        """--include-indirect --json produces valid JSON with expected keys."""
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest", "dorin shieldarm",
                       "--include-indirect", "--json",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "subjects" in data
        assert "shared_events" in data

    def test_rel_year_to_filter(self, df_root: Path, sample_xml_path: Path) -> None:
        """--year-to 100 excludes year-101+ shared events."""
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest", "dorin shieldarm",
                       "--year-to", "100", "--json",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        data = json.loads(r.stdout)
        # The only shared event (spouse link, year 101) must be filtered out
        for ev in data["shared_events"]["events"]:
            assert int(ev["year"]) <= 100

    def test_rel_year_single_filter(self, df_root: Path, sample_xml_path: Path) -> None:
        """--year 100 restricts shared events to exactly year 100."""
        r = run_script(df_root, "relationship_history.py",
                       "urist mctest", "dorin shieldarm",
                       "--year", "100", "--json",
                       xml_path=str(sample_xml_path))
        assert r.returncode == 0
        data = json.loads(r.stdout)
        for ev in data["shared_events"]["events"]:
            assert int(ev["year"]) == 100

    def test_rel_not_found(self, df_root: Path, sample_xml_path: Path) -> None:
        """Nonexistent names → error."""
        r = run_script(df_root, "relationship_history.py",
                       "nonexistent1", "nonexistent2",
                       xml_path=str(sample_xml_path))
        assert r.returncode != 0
        assert "no historical figure" in r.stderr.lower() or "error" in r.stderr.lower()


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
        data = json.loads(r.stdout)
        assert "direct_relationships" in data
        # No direct link between these two
        assert len(data["direct_relationships"]) == 0
