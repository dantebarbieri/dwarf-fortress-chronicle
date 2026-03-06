"""
moods.py — Mood, artifact creation, and masterwork tracker for Dwarf Fortress Legends XML.

Tracks strange moods, artifact creation, and masterwork production by figure
and year.  Groups results by historical figure, showing total masterworks and
any artifacts created, along with skill level at time of creation.

Usage examples:
    python scripts/moods.py --year 100
    python scripts/moods.py --year-from 99 --year-to 102 --site testfort
    python scripts/moods.py --figure "urist mctest" --json
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.legends_parser import (
    LegendsParser,
    add_common_args,
    configure_output,
    event_involves_hf,
    event_involves_site,
    get_parser_from_args,
    print_json,
)


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def _collect_events(
    parser: LegendsParser,
    year_from: int | None,
    year_to: int | None,
    site_id: str | None,
    hf_id: str | None,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (masterpiece_events, artifact_events, mood_events) filtered."""
    masterpieces: list[dict] = []
    artifacts: list[dict] = []
    moods: list[dict] = []

    for ev in parser.filter_events(year_from=year_from, year_to=year_to,
                                    site_id=site_id, hf_id=hf_id):
        etype = ev.get("type", "")
        if etype == "masterpiece item":
            masterpieces.append(ev)
        elif etype == "artifact created":
            artifacts.append(ev)
        elif etype == "change hf state":
            mood = ev.get("mood", "-1")
            if mood not in ("-1", "", None):
                moods.append(ev)

    return masterpieces, artifacts, moods


# ---------------------------------------------------------------------------
# Grouping by figure
# ---------------------------------------------------------------------------

def _figure_key(ev: dict) -> str:
    """Extract the relevant HF ID from an event."""
    return str(ev.get("maker_hfid") or ev.get("hfid") or "-1")


def _group_by_figure(
    masterpieces: list[dict],
    artifacts: list[dict],
    moods: list[dict],
) -> dict[str, list[dict]]:
    """Group all events by figure, sorted by year/seconds72 within each group."""
    groups: dict[str, list[dict]] = defaultdict(list)

    for ev in masterpieces:
        fid = _figure_key(ev)
        if fid != "-1":
            groups[fid].append(ev)
    for ev in artifacts:
        fid = str(ev.get("hfid", "-1"))
        if fid != "-1":
            groups[fid].append(ev)
    for ev in moods:
        fid = str(ev.get("hfid", "-1"))
        if fid != "-1":
            groups[fid].append(ev)

    # Sort each figure's events chronologically
    for fid in groups:
        groups[fid].sort(key=lambda e: (int(e.get("year", 0)), int(e.get("seconds72", 0))))

    return dict(groups)


# ---------------------------------------------------------------------------
# Output — text
# ---------------------------------------------------------------------------

def _figure_label(hf_id: str, parser: LegendsParser) -> str:
    """Name (AssociatedType) label for a figure."""
    hf = parser.hf_map.get(str(hf_id))
    if not hf:
        return f"Unknown ({hf_id})"
    name = (hf.get("name") or "Unnamed").title()
    assoc = hf.get("associated_type", "")
    if assoc and assoc != "STANDARD":
        return f"{name} ({assoc.replace('_', ' ').title()})"
    return name


def _artifact_label(artifact_id: str, parser: LegendsParser) -> str:
    """Return 'Name (item_type)' for an artifact, or fallback."""
    art = parser.artifact_map.get(str(artifact_id))
    if not art:
        return f"Artifact {artifact_id}"
    name = (art.get("name_string") or art.get("name") or "unnamed").title()
    item = art.get("item", "item")
    return f'"{name}" ({item})'


def _print_text(
    groups: dict[str, list[dict]],
    parser: LegendsParser,
    year_from: int | None,
    year_to: int | None,
) -> None:
    """Print human-readable grouped output."""
    # Header
    if year_from is not None and year_to is not None and year_from != year_to:
        print(f"Moods & Masterworks: Year {year_from}\u2013{year_to}")
    elif year_from is not None:
        print(f"Moods & Masterworks: Year {year_from}")
    elif year_to is not None:
        print(f"Moods & Masterworks: through Year {year_to}")
    else:
        print("Moods & Masterworks")
    print("=" * 40)
    print()

    total_masterworks = 0
    total_artifacts = 0

    if not groups:
        print("No mood or masterwork events found.")
        print()
        print("--- 0 figure(s), 0 masterwork(s), 0 artifact(s) ---")
        return

    # Aggregate masterpieces per figure per year for concise display
    for hf_id in sorted(groups, key=lambda fid: (
        (parser.hf_map.get(fid) or {}).get("name", "zzz"),
    )):
        events = groups[hf_id]
        label = _figure_label(hf_id, parser)
        print(f"{label}:")

        # Group masterpieces by year for concise display
        year_masterpieces: dict[int, list[dict]] = defaultdict(list)
        other_events: list[dict] = []

        for ev in events:
            if ev.get("type") == "masterpiece item":
                yr = int(ev.get("year", 0))
                year_masterpieces[yr].append(ev)
            else:
                other_events.append(ev)

        # Interleave by year: collect all printable lines with sort key
        lines: list[tuple[int, int, str]] = []

        for yr, mps in year_masterpieces.items():
            total_masterworks += len(mps)
            skill = mps[0].get("skill_at_time", "?")
            lines.append((yr, 0, f"  Year {yr}: {len(mps)} masterwork(s) (skill level: {skill})"))

        for ev in other_events:
            yr = int(ev.get("year", 0))
            sec = int(ev.get("seconds72", 0))
            if ev.get("type") == "artifact created":
                total_artifacts += 1
                art_id = ev.get("artifact_id", "")
                alabel = _artifact_label(art_id, parser)
                lines.append((yr, sec, f"  Year {yr}: Created artifact {alabel}"))
            elif ev.get("type") == "change hf state":
                mood = ev.get("mood", "unknown")
                lines.append((yr, sec, f"  Year {yr}: Entered mood state: {mood}"))

        lines.sort()
        for _, _, line in lines:
            print(line)
        print()

    print(f"--- {len(groups)} figure(s), {total_masterworks} masterwork(s), {total_artifacts} artifact(s) ---")


# ---------------------------------------------------------------------------
# Output — JSON
# ---------------------------------------------------------------------------

def _build_json(
    groups: dict[str, list[dict]],
    parser: LegendsParser,
) -> list[dict[str, Any]]:
    """Build structured JSON output."""
    result: list[dict[str, Any]] = []
    for hf_id, events in groups.items():
        hf = parser.hf_map.get(str(hf_id)) or {}
        name = (hf.get("name") or "Unknown").title()
        assoc = hf.get("associated_type", "")

        masterworks: list[dict[str, Any]] = []
        artifacts_created: list[dict[str, Any]] = []
        mood_changes: list[dict[str, Any]] = []

        for ev in events:
            etype = ev.get("type", "")
            if etype == "masterpiece item":
                masterworks.append({
                    "year": int(ev.get("year", 0)),
                    "skill_at_time": ev.get("skill_at_time", None),
                    "event_id": ev.get("id"),
                })
            elif etype == "artifact created":
                art_id = ev.get("artifact_id", "")
                art = parser.artifact_map.get(str(art_id)) or {}
                artifacts_created.append({
                    "year": int(ev.get("year", 0)),
                    "artifact_id": art_id,
                    "artifact_name": (art.get("name") or "unknown").title(),
                    "artifact_type": art.get("item", "unknown"),
                    "event_id": ev.get("id"),
                })
            elif etype == "change hf state":
                mood_changes.append({
                    "year": int(ev.get("year", 0)),
                    "mood": ev.get("mood", "unknown"),
                    "event_id": ev.get("id"),
                })

        result.append({
            "hf_id": hf_id,
            "name": name,
            "profession": assoc,
            "masterworks": masterworks,
            "artifacts": artifacts_created,
            "mood_changes": mood_changes,
            "total_masterworks": len(masterworks),
            "total_artifacts": len(artifacts_created),
        })
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Track moods, artifact creation, and masterwork production.",
    )
    add_common_args(ap)
    ap.add_argument("--site", type=str, default=None, help="Filter by site name or ID.")
    ap.add_argument("--figure", type=str, default=None, help="Filter by figure name or ID.")
    return ap


def main() -> None:
    configure_output()
    ap = build_parser()
    args = ap.parse_args()

    # Require at least one year filter
    if not any([args.year, args.year_from, args.year_to]):
        ap.error("At least one year filter is required: --year, --year-from, or --year-to.")

    # Normalise year args
    year_from: int | None = args.year if args.year else args.year_from
    year_to: int | None = args.year if args.year else args.year_to

    with get_parser_from_args(args) as parser:
        # Resolve human-friendly names to IDs
        site_id: str | None = None
        hf_id: str | None = None

        if args.site:
            site_id = parser.resolve_site_id(args.site)
        if args.figure:
            hf_id = parser.resolve_hf_id(args.figure)

        masterpieces, artifacts, moods = _collect_events(
            parser, year_from, year_to, site_id, hf_id,
        )
        groups = _group_by_figure(masterpieces, artifacts, moods)

        if args.json:
            print_json(_build_json(groups, parser))
        else:
            _print_text(groups, parser, year_from, year_to)


if __name__ == "__main__":
    main()
