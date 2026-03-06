"""Tests for figure_skills.py — skill tables, comparisons, and filtering.

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
# figure_skills.py
# ===================================================================


class TestDwarfSkills:
    """Tests for figure_skills.py."""

    SCRIPT = "figure_skills.py"

    def test_skills_table(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        # PLANT at 16000 IP → Expert
        assert "PLANT" in out
        assert "Expert" in out
        # RECORD_KEEPING at 5500 IP → Skilled
        assert "RECORD_KEEPING" in out
        assert "Skilled" in out
        # MINING at 3000 IP → Competent
        assert "MINING" in out
        assert "Competent" in out

    def test_skills_sorted(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        # PLANT (highest IP 16000) should appear before MINING (3000)
        plant_pos = out.index("PLANT")
        mining_pos = out.index("MINING")
        assert plant_pos < mining_pos

    def test_skills_json(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", "--json", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "skills" in data
        assert isinstance(data["skills"], list)
        assert len(data["skills"]) > 0
        # Skills should be sorted by IP descending (default sort = level)
        ips = [s["total_ip"] for s in data["skills"]]
        assert ips == sorted(ips, reverse=True)

    def test_skills_combat_fighter(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "dorin shieldarm", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        # HAMMER at 18700 IP → Professional
        assert "HAMMER" in out
        assert "Professional" in out

    def test_skills_compare(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, self.SCRIPT,
            "urist mctest", "--compare", "dorin shieldarm",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Comparison header with both names
        assert "comparison" in out or "vs" in out
        # Both figures' skills present
        assert "plant" in out
        assert "hammer" in out

    def test_skills_min_level(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, self.SCRIPT,
            "urist mctest", "--min-level", "Proficient",
            xml_path=str(sample_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout
        # PLANT (Expert) is above Proficient → shown
        assert "PLANT" in out
        # MINING (Competent) is below Proficient → not in the skills table
        # WRESTLING (Novice) also below
        # Check that the table portion does not contain Competent or Novice level skills
        # (the word "MINING" might appear in category summary only if present, but
        # min-level filters it from both display and categories)
        assert "Competent" not in out
        assert "Novice" not in out

    def test_skills_goblin(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "snagak goretooth", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        # WHIP at 23500 IP → Accomplished
        assert "WHIP" in out
        assert "Accomplished" in out


# ===================================================================
# Figure with no skills
# ===================================================================


class TestFigureNoSkills:
    """figure_skills.py should handle figures with minimal skills gracefully."""

    SCRIPT = "figure_skills.py"

    def test_great_grandchild_minimal_skills(self, df_root: Path, complex_families_xml_path: Path) -> None:
        """Cilob (821) has only WRESTLING at 500 IP (Novice) — should still show."""
        r = run_script(df_root, self.SCRIPT, "cilob ironbeard", xml_path=str(complex_families_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        assert "WRESTLING" in out
        assert "Novice" in out

    def test_dragon_no_skills(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        """Scald cinderjaw (714) has no skills — should not crash."""
        r = run_script(df_root, self.SCRIPT, "scald cinderjaw", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "scald cinderjaw" in out
        assert "no skills" in out or "skill" in out
