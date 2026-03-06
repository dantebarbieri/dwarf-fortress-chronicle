"""Tests for deaths.py — death/obituary tracker.

Exercises CLI behaviour via subprocess (exit codes, stdout, JSON), and
unit-tests core logic via direct imports.
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
    DORIN_ID,
    SNAGAK_ID,
    DWARF_CIV_ID,
    GOBLIN_CIV_ID,
    TESTFORT_ID,
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_DF_ROOT = Path(__file__).resolve().parent.parent.parent


def run_deaths(
    *args: str,
    xml_path: str,
    df_root: Path = _DF_ROOT,
) -> subprocess.CompletedProcess:
    """Run deaths.py from the DF root directory."""
    cmd = [
        sys.executable,
        "scripts/deaths.py",
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
# Tests using base_world.xml
# ===================================================================


class TestBaseWorldDeaths:
    """Tests against the base_world.xml fixture (Snagak dies year 101)."""

    def test_death_year_101_at_testfort(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """Event 1011: Snagak Goretooth dies at testfort in year 101."""
        r = run_deaths("--year", "101", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "snagak goretooth" in out
        assert "goblin" in out
        assert "testfort" in out

    def test_slayer_resolved(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """Slayer (Dorin Shieldarm) is resolved from slayer_hfid."""
        r = run_deaths("--year", "101", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "dorin shieldarm" in out
        assert "dwarf" in out

    def test_age_at_death(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """Snagak: born year 10, died year 101 → age 91."""
        r = run_deaths("--year", "101", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        assert "age 91" in r.stdout.lower()

    def test_year_filtering_no_deaths(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """Year 99 has no deaths in base_world."""
        r = run_deaths("--year", "99", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        assert "0 death(s)" in r.stdout.lower()

    def test_site_filtering(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """--site testfort finds Snagak's death."""
        r = run_deaths(
            "--year", "101", "--site", "testfort",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "snagak goretooth" in out

    def test_entity_filtering(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """--entity 'dark horde' finds Snagak (member of goblin civ 102)."""
        r = run_deaths(
            "--year", "101", "--entity", "the dark horde",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "snagak goretooth" in out

    def test_entity_filtering_excludes_non_members(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """--entity 'guilds of testing' excludes Snagak (not a member)."""
        r = run_deaths(
            "--year", "101", "--entity", "guilds of testing",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "snagak goretooth" not in out
        assert "0 death(s)" in out

    def test_json_output_valid(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """--json produces valid JSON with expected fields."""
        r = run_deaths(
            "--year", "101", "--json",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert len(data) == 1
        rec = data[0]
        assert rec["name"] == "Snagak Goretooth"
        assert rec["race"] == "GOBLIN"
        assert rec["age"] == 91
        assert rec["cause"] == "struck"
        assert rec["slayer"]["name"] == "Dorin Shieldarm"
        assert rec["site"] == "testfort"

    def test_no_deaths_empty_range(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """Year range with no deaths returns cleanly."""
        r = run_deaths(
            "--year-from", "1", "--year-to", "5",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, r.stderr
        assert "0 death(s)" in r.stdout.lower()

    def test_missing_year_filter_error(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """Missing year filter produces an error."""
        r = run_deaths(xml_path=str(base_world_xml_path))
        assert r.returncode != 0
        combined = (r.stdout + r.stderr).lower()
        assert "year" in combined


# ===================================================================
# Tests using dead_figures.xml
# ===================================================================


class TestDeadFigures:
    """Tests against the dead_figures.xml fixture (multiple death causes)."""

    def test_multiple_deaths_in_range(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """Year range 80–95 should find all five deaths."""
        r = run_deaths(
            "--year-from", "80", "--year-to", "95",
            xml_path=str(dead_figures_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "5 death(s)" in out

    def test_old_age_death(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """Erush died of old age in year 80."""
        r = run_deaths(
            "--year", "80",
            xml_path=str(dead_figures_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "erush lonelypick" in out
        assert "old age" in out

    def test_drowned_death(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """Bomrek drowned in year 85."""
        r = run_deaths(
            "--year", "85",
            xml_path=str(dead_figures_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "bomrek wetlungs" in out
        assert "drowned" in out

    def test_thirst_death(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """Tirist died of thirst in year 92."""
        r = run_deaths(
            "--year", "92",
            xml_path=str(dead_figures_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "tirist dustthroat" in out
        assert "thirst" in out

    def test_megabeast_slayer(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """Asmel killed by dragon Scald in year 90."""
        r = run_deaths(
            "--year", "90",
            xml_path=str(dead_figures_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "asmel brightiron" in out
        assert "scald cinderjaw" in out
        assert "dragon" in out

    def test_age_calculation_negative_birth(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """Erush: born -100, died 80 → age 180."""
        r = run_deaths(
            "--year", "80", "--json",
            xml_path=str(dead_figures_xml_path),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        erush = [d for d in data if "erush" in d["name"].lower()]
        assert len(erush) == 1
        assert erush[0]["age"] == 180

    def test_json_all_deaths(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """JSON output for full range returns all deaths."""
        r = run_deaths(
            "--year-from", "1", "--year-to", "200", "--json",
            xml_path=str(dead_figures_xml_path),
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert len(data) == 5
        causes = {d["cause"] for d in data}
        assert causes == {"struck", "old age", "drowned", "thirst"}

    def test_site_filter_gravehall(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """All deaths in dead_figures.xml are at gravehall."""
        r = run_deaths(
            "--year-from", "1", "--year-to", "200",
            "--site", "gravehall",
            xml_path=str(dead_figures_xml_path),
        )
        assert r.returncode == 0, r.stderr
        assert "5 death(s)" in r.stdout.lower()

    def test_entity_filter_order_of_graves(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """Entity 700 (order of graves) contains most dead figures."""
        r = run_deaths(
            "--year-from", "1", "--year-to", "200",
            "--entity", "the order of graves",
            xml_path=str(dead_figures_xml_path),
        )
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        # All 5 dead figures are members of entity 700; Scald (714) is alive
        assert "5 death(s)" in out
