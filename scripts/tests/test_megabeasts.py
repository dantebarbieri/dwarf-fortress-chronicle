"""Tests for megabeasts.py.

Exercises the CLI with base_world.xml (dead dragon, no kills) and
dead_figures.xml (living dragon with 1 kill).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.tests.conftest import DRAGON_ID


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run_megabeasts(
    df_root: Path,
    *args: str,
    xml_path: str,
) -> subprocess.CompletedProcess:
    """Run megabeasts.py from the DF root directory."""
    cmd = [
        sys.executable,
        "scripts/megabeasts.py",
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
# Tests using base_world.xml (dragon HF 303, dead, zero kills)
# ===================================================================


class TestMegabeastsBaseWorld:
    """Tests against the base_world fixture."""

    def test_lists_dragon(self, df_root: Path, base_world_xml_path: Path) -> None:
        """The dragon should appear in default output."""
        r = run_megabeasts(df_root, xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "blaze firemaw" in out
        assert "dragon" in out

    def test_dragon_status_dead(self, df_root: Path, base_world_xml_path: Path) -> None:
        """Dragon should show as dead in year 50."""
        r = run_megabeasts(df_root, xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "dead" in out
        assert "50" in out

    def test_alive_only_excludes_dead_dragon(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """--alive-only should exclude the dead dragon."""
        r = run_megabeasts(df_root, "--alive-only", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        assert "blaze firemaw" not in r.stdout.lower()
        assert "0 megabeast(s) found" in r.stdout.lower()

    def test_dead_only_includes_dead_dragon(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """--dead-only should include the dead dragon."""
        r = run_megabeasts(df_root, "--dead-only", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "blaze firemaw" in out
        assert "1 megabeast(s) found" in out

    def test_json_output_valid(self, df_root: Path, base_world_xml_path: Path) -> None:
        """--json should produce valid JSON with the dragon."""
        r = run_megabeasts(df_root, "--json", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert len(data) >= 1
        dragon = next(e for e in data if e["race"].upper() == "DRAGON")
        assert dragon["id"] == DRAGON_ID
        assert dragon["alive"] is False

    def test_race_filter_dragon(self, df_root: Path, base_world_xml_path: Path) -> None:
        """--race DRAGON should return only the dragon."""
        r = run_megabeasts(df_root, "--race", "DRAGON", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "dragon" in out
        assert "1 megabeast(s) found" in out

    def test_race_filter_no_match(self, df_root: Path, base_world_xml_path: Path) -> None:
        """--race GIANT should return nothing in base_world."""
        r = run_megabeasts(df_root, "--race", "GIANT", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        assert "0 megabeast(s) found" in r.stdout.lower()

    def test_kill_count_zero(self, df_root: Path, base_world_xml_path: Path) -> None:
        """The base-world dragon has zero kills."""
        r = run_megabeasts(df_root, "--json", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        dragon = next(e for e in data if e["id"] == DRAGON_ID)
        assert dragon["kill_count"] == 0

    def test_min_kills_excludes_base_dragon(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """--min-kills 1 should exclude the zero-kill dragon."""
        r = run_megabeasts(df_root, "--min-kills", "1", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        assert "0 megabeast(s) found" in r.stdout.lower()

    def test_spheres_shown(self, df_root: Path, base_world_xml_path: Path) -> None:
        """Dragon spheres (fire, wealth) should appear."""
        r = run_megabeasts(df_root, xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "fire" in out
        assert "wealth" in out


# ===================================================================
# Tests using dead_figures.xml (dragon HF 714, alive, 1 kill)
# ===================================================================


class TestMegabeastsDeadFigures:
    """Tests against the dead_figures fixture (dragon Scald with kills)."""

    def test_lists_dragon_with_kills(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """Scald Cinderjaw should appear with kill count."""
        r = run_megabeasts(df_root, xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        out = r.stdout.lower()
        assert "scald cinderjaw" in out
        assert "dragon" in out
        assert "1 known" in out

    def test_kill_tracking(self, df_root: Path, dead_figures_xml_path: Path) -> None:
        """JSON output should show Scald's kill of Asmel."""
        r = run_megabeasts(df_root, "--json", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        scald = next(e for e in data if e["id"] == "714")
        assert scald["kill_count"] == 1
        assert scald["kills"][0]["victim_name"].lower() == "asmel brightiron"
        assert scald["alive"] is True

    def test_alive_only_includes_scald(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """--alive-only should include the living dragon Scald."""
        r = run_megabeasts(df_root, "--alive-only", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        assert "scald cinderjaw" in r.stdout.lower()

    def test_dead_only_excludes_scald(
        self, df_root: Path, dead_figures_xml_path: Path
    ) -> None:
        """--dead-only should exclude the living dragon Scald."""
        r = run_megabeasts(df_root, "--dead-only", xml_path=str(dead_figures_xml_path))
        assert r.returncode == 0, r.stderr
        assert "scald cinderjaw" not in r.stdout.lower()


# ===================================================================
# Smoke tests: inherited common flags that are no-ops
# ===================================================================


class TestMegabeastsCommonFlagsNoop:
    """Verify inherited --year/--year-from/--year-to flags don't crash."""

    def test_year_flag_accepted(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """--year is accepted without crashing (flag is a no-op)."""
        r = run_megabeasts(df_root, "--year", "100", xml_path=str(base_world_xml_path))
        assert r.returncode == 0, r.stderr

    def test_year_range_flags_accepted(
        self, df_root: Path, base_world_xml_path: Path
    ) -> None:
        """--year-from/--year-to are accepted without crashing (flags are no-ops)."""
        r = run_megabeasts(
            df_root, "--year-from", "50", "--year-to", "100",
            xml_path=str(base_world_xml_path),
        )
        assert r.returncode == 0, r.stderr
