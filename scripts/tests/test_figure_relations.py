"""Tests for figure_relations.py — relationships and family trees.

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

    def test_all_flag_runs_without_error(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", "--all", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr

    def test_all_flag_json(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", "--all", "--json", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "social_links" in data
        assert "family" in data

    def test_year_flags_accepted(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, self.SCRIPT, "urist mctest", "--year", "100", xml_path=str(sample_xml_path))
        assert r.returncode == 0, r.stderr


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
