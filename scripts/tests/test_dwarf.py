"""Tests for figure.py, figure_relations.py, and figure_skills.py.

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
    DORIN_ID,
    SNAGAK_ID,
    DRAGON_ID,
    KIDDO_ID,
    DWARF_CIV_ID,
    SITE_GOV_ID,
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
# figure_relations.py
# ===================================================================


class TestDwarfRelations:
    """Tests for figure_relations.py."""

    SCRIPT = "figure_relations.py"

    def test_relations_family(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "dorin shieldarm" in out
        assert "kiddo mctest" in out

    def test_relations_deity(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Deity link to dragon blaze firemaw
        assert "blaze firemaw" in out or "deity" in out

    def test_relations_entity(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "guilds of testing" in out or "entity" in out

    def test_relations_tree(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", "--tree", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        # Tree uses bracket notation [Name] and pipe characters
        assert "[" in out and "]" in out
        assert "|" in out
        # Subject's name should appear in the tree
        assert "Urist Mctest" in out

    def test_relations_json(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", "--json", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "family" in data
        assert "deity_links" in data
        assert "entity_relationships" in data

    def test_relations_child_parents(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "kiddo mctest", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Kiddo's parents: father Urist, mother Dorin
        assert "urist mctest" in out
        assert "dorin shieldarm" in out


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
        import json
        data = json.loads(r.stdout)
        assert data["identity"]["death_year"] == "95"


# ===================================================================
# Complex family tree (complex_families.xml)
# ===================================================================


class TestComplexFamilyTree:
    """figure_relations.py --tree should display multi-generation tree."""

    SCRIPT = "figure_relations.py"

    def test_tree_grandparent(self, df_root: Path, complex_families_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "eral gemheart", "--tree", xml_path=str(complex_families_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        # Tree should show Eral and her descendants
        assert "Eral Gemheart" in out
        assert "[" in out and "]" in out
        assert "|" in out

    def test_tree_middle_generation(self, df_root: Path, complex_families_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "tosid ironbeard", "--tree", xml_path=str(complex_families_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        assert "Tosid Ironbeard" in out
        # Should show parents and children
        assert "Dastot Ironbeard" in out or "Eral Gemheart" in out

    def test_relations_grandchild(self, df_root: Path, complex_families_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "led ironbeard", xml_path=str(complex_families_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Should list parents
        assert "tosid ironbeard" in out
        assert "aban copperkettle" in out

    def test_relations_divorced_parents(self, df_root: Path, complex_families_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "mafol wanderstone", xml_path=str(complex_families_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # Mafol's parents (divorced)
        assert "udil ironbeard" in out or "rovod wanderstone" in out

    def test_tree_great_grandchild(self, df_root: Path, complex_families_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "cilob ironbeard", "--tree", xml_path=str(complex_families_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout
        assert "Cilob Ironbeard" in out


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
