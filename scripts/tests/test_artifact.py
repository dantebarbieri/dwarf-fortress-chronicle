"""Tests for artifact.py CLI script using the sample XML fixture."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# conftest.py is loaded automatically by pytest; import constants directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import (  # noqa: E402
    URIST_ID,
    DORIN_ID,
    GLEAMCUTTER_ID,
    DARKBANE_ID,
    DWARF_CIV_ID,
    TESTFORT_ID,
)


def run_script(
    df_root: Path, script_name: str, *args: str, xml_path: str
) -> subprocess.CompletedProcess:
    """Run a script as a subprocess and return the result.

    ``--xml`` is placed *after* positional/subcommand args so that
    argparse subparsers (e.g. battle.py wars) receive it correctly.
    """
    cmd = [sys.executable, f"scripts/{script_name}", *args, "--xml", xml_path]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(df_root),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


# ===================================================================
# artifact.py tests
# ===================================================================


class TestArtifactListAll:
    def test_artifact_list_all(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "artifact.py", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "gleamcutter" in out
        assert "darkbane" in out


class TestArtifactDetailByName:
    def test_artifact_detail_by_name(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "artifact.py", "gleamcutter", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "gleamcutter" in out
        assert "weapon" in out
        assert "urist" in out
        assert "testfort" in out


class TestArtifactDetailById:
    def test_artifact_detail_by_id(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "artifact.py", "400", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "gleamcutter" in out
        assert "weapon" in out
        assert "urist" in out
        assert "testfort" in out


class TestArtifactDarkbaneDetail:
    def test_artifact_darkbane_detail(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "artifact.py", "darkbane", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "shield" in out
        assert "no current holder" in out or "none" in out
        assert "fiery sunset" in out


class TestArtifactHistory:
    def test_artifact_history(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "artifact.py", "gleamcutter", xml_path=str(sample_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        # Should show creation event (year 100) and stored event
        assert "created" in out
        assert "100" in out
        assert "stored" in out


class TestArtifactJson:
    def test_artifact_json(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, "artifact.py", "gleamcutter", "--json", xml_path=str(sample_xml_path)
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        data = json.loads(r.stdout)
        assert isinstance(data, dict)
        assert data["id"] == "400"
        assert "gleamcutter" in data["name"].lower()
        assert data["history"] is not None
        assert len(data["history"]) >= 1


class TestArtifactListBySite:
    def test_artifact_list_by_site(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(
            df_root, "artifact.py", "--site", "testfort", xml_path=str(sample_xml_path)
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "gleamcutter" in out
        assert "darkbane" in out


class TestArtifactNotFound:
    def test_artifact_not_found(self, df_root: Path, sample_xml_path: Path) -> None:
        r = run_script(df_root, "artifact.py", "nonexistent", xml_path=str(sample_xml_path))
        # Should either exit non-zero or print an error message
        assert r.returncode != 0 or "no artifact found" in r.stderr.lower() or "error" in r.stderr.lower()


# ===================================================================
# Artifacts in empty world
# ===================================================================


class TestArtifactEmptyWorld:
    """Artifacts in empty_world.xml should return appropriate message."""

    def test_artifact_list_empty(self, df_root: Path, empty_world_xml_path: Path) -> None:
        r = run_script(df_root, "artifact.py", xml_path=str(empty_world_xml_path))
        assert r.returncode == 0, f"stderr: {r.stderr}"
        out = r.stdout.lower()
        assert "no artifact" in out or "0 artifact" in out or out.strip() == ""

    def test_artifact_search_empty(self, df_root: Path, empty_world_xml_path: Path) -> None:
        r = run_script(df_root, "artifact.py", "anything", xml_path=str(empty_world_xml_path))
        combined = (r.stdout + r.stderr).lower()
        assert "no artifact" in combined or "error" in combined or r.returncode != 0
