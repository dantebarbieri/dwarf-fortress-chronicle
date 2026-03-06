"""Tests for moods.py CLI script using the sample XML fixture."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import (  # noqa: E402
    URIST_ID,
    DORIN_ID,
    GLEAMCUTTER_ID,
    DARKBANE_ID,
    TESTFORT_ID,
)


def run_script(
    df_root: Path, *args: str, xml_path: str
) -> subprocess.CompletedProcess:
    """Run moods.py as a subprocess and return the result."""
    cmd = [sys.executable, "scripts/moods.py", *args, "--xml", xml_path]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(df_root),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


# ===================================================================
# 1. Year 100 shows Urist's masterpieces and artifact creation
# ===================================================================

class TestYear100Urist:
    def test_urist_masterpieces_in_year_100(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "--year", "100", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "urist" in out
        assert "masterwork" in out
        assert "2 masterwork" in out

    def test_urist_artifact_in_year_100(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "--year", "100", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "gleamcutter" in out
        assert "weapon" in out


# ===================================================================
# 2. Year 100–102 shows both figures' work
# ===================================================================

class TestYearRange:
    def test_both_figures_in_range(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "--year-from", "100", "--year-to", "102", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "urist" in out
        assert "dorin" in out
        assert "gleamcutter" in out
        assert "darkbane" in out


# ===================================================================
# 3. --figure filtering works
# ===================================================================

class TestFigureFilter:
    def test_filter_urist_only(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, "--year-from", "100", "--year-to", "102",
            "--figure", "urist mctest",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "urist" in out
        assert "dorin" not in out

    def test_filter_dorin_only(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, "--year-from", "100", "--year-to", "102",
            "--figure", "dorin shieldarm",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "dorin" in out
        assert "urist" not in out


# ===================================================================
# 4. --site testfort filters correctly
# ===================================================================

class TestSiteFilter:
    def test_site_testfort(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, "--year-from", "100", "--year-to", "102",
            "--site", "testfort",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        # All events in sample XML are at testfort
        assert "urist" in out or "dorin" in out


# ===================================================================
# 5. JSON output is valid with expected structure
# ===================================================================

class TestJsonOutput:
    def test_json_valid(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, "--year-from", "100", "--year-to", "102", "--json",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_json_structure(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, "--year-from", "100", "--year-to", "102", "--json",
            xml_path=str(sample_xml_path),
        )
        data = json.loads(r.stdout)
        for entry in data:
            assert "hf_id" in entry
            assert "name" in entry
            assert "profession" in entry
            assert "masterworks" in entry
            assert "artifacts" in entry
            assert "total_masterworks" in entry
            assert "total_artifacts" in entry

    def test_json_figure_filter(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, "--year-from", "100", "--year-to", "102",
            "--figure", "urist mctest", "--json",
            xml_path=str(sample_xml_path),
        )
        data = json.loads(r.stdout)
        assert len(data) == 1
        assert data[0]["hf_id"] == URIST_ID
        assert data[0]["total_masterworks"] == 2
        assert data[0]["total_artifacts"] == 1


# ===================================================================
# 6. Year with no events returns empty gracefully
# ===================================================================

class TestEmptyResults:
    def test_year_with_no_events(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "--year", "50", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "0 figure(s)" in out
        assert "0 masterwork(s)" in out

    def test_empty_world(self, df_root: Path, empty_world_xml_path: Path) -> None:
        r = run_script(df_root, "--year", "100", xml_path=str(empty_world_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "0 figure(s)" in out


# ===================================================================
# 7. Summary counts are correct
# ===================================================================

class TestSummaryCounts:
    def test_year_100_counts(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "--year", "100", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        # Year 100: 2 masterworks (both Urist), 2 artifacts (Urist + Dorin)
        assert "2 masterwork(s)" in out
        assert "2 artifact(s)" in out
        assert "2 figure(s)" in out

    def test_full_range_counts(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, "--year-from", "100", "--year-to", "102",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout
        # Total: 3 masterworks (2 Urist yr100, 1 Dorin yr102), 2 artifacts
        # The summary line is at the end
        lines = out.strip().split("\n")
        summary = lines[-1].lower()
        assert "3 masterwork(s)" in summary
        assert "2 artifact(s)" in summary


# ===================================================================
# 8. Skill level at time is shown
# ===================================================================

class TestSkillLevel:
    def test_skill_level_shown_text(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "--year", "100", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout
        assert "skill level: 14" in out

    def test_skill_level_shown_json(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, "--year-from", "100", "--year-to", "102", "--json",
            xml_path=str(sample_xml_path),
        )
        data = json.loads(r.stdout)
        skill_values = []
        for entry in data:
            for mw in entry["masterworks"]:
                if mw["skill_at_time"] is not None:
                    skill_values.append(mw["skill_at_time"])
        assert "14" in skill_values
        assert "28" in skill_values


# ===================================================================
# 9. Artifact names are resolved from artifact map
# ===================================================================

class TestArtifactNameResolution:
    def test_gleamcutter_resolved(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "--year", "100", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "gleamcutter" in out

    def test_darkbane_resolved(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "--year", "100", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "darkbane" in out

    def test_json_artifact_names(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, "--year-from", "100", "--year-to", "102", "--json",
            xml_path=str(sample_xml_path),
        )
        data = json.loads(r.stdout)
        artifact_names = []
        for entry in data:
            for art in entry["artifacts"]:
                artifact_names.append(art["artifact_name"].lower())
        assert "gleamcutter" in artifact_names
        assert "darkbane" in artifact_names


# ===================================================================
# Error handling
# ===================================================================

class TestErrorHandling:
    def test_no_year_filter_errors(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, xml_path=str(sample_xml_path))
        assert r.returncode != 0
