"""
artifact.py — Show artifact details from the Dwarf Fortress Legends XML.

Usage:
    python scripts/artifact.py                     # list all artifacts
    python scripts/artifact.py "elemental"         # detail view for matching artifact
    python scripts/artifact.py --site luregold     # filter by site
    python scripts/artifact.py --holder atir       # filter by holder
    python scripts/artifact.py --list --json       # list mode, JSON output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

# Ensure the DF root directory is on sys.path so `from scripts.legends_parser`
# resolves correctly when invoked as `python scripts/artifact.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.legends_parser import (
    LegendsParser,
    add_common_args,
    configure_output,
    format_hf_summary,
    format_year,
    get_parser_from_args,
    print_json,
)

# Event types that involve artifacts
_ARTIFACT_EVENT_TYPES: list[str] = [
    "artifact created",
    "artifact stored",
    "artifact given",
    "artifact lost",
    "artifact found",
    "artifact possessed",
    "artifact recovered",
    "artifact claim formed",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_item_description(artifact: dict) -> str:
    """Extract a human-readable item description from an artifact dict."""
    item = artifact.get("item")
    if isinstance(item, dict):
        parts: list[str] = []
        item_type = item.get("item_type") or item.get("type") or ""
        item_subtype = item.get("item_subtype") or item.get("subtype") or ""
        material = item.get("mat") or item.get("material") or ""
        if material:
            parts.append(material.replace("_", " ").title())
        if item_subtype:
            parts.append(item_subtype.replace("_", " ").title())
        elif item_type:
            parts.append(item_type.replace("_", " ").title())
        return " ".join(parts) if parts else "Unknown item"
    if isinstance(item, str) and item:
        return item
    # Fallback: check for item_type / item_subtype as top-level keys
    item_type = artifact.get("item_type") or artifact.get("type") or ""
    item_subtype = artifact.get("item_subtype") or artifact.get("subtype") or ""
    mat = artifact.get("mat") or artifact.get("material") or ""
    parts = []
    if mat:
        parts.append(mat.replace("_", " ").title())
    if item_subtype:
        parts.append(item_subtype.replace("_", " ").title())
    elif item_type:
        parts.append(item_type.replace("_", " ").title())
    return " ".join(parts) if parts else "Artifact"


def _get_artifact_events(parser: LegendsParser, artifact_id: str) -> list[dict]:
    """Return all events involving *artifact_id*, sorted by year."""
    aid = str(artifact_id)
    matching: list[dict] = []
    for ev in parser.events:
        if ev.get("type") in _ARTIFACT_EVENT_TYPES and str(ev.get("artifact_id", "")) == aid:
            matching.append(ev)
    matching.sort(key=lambda e: int(e.get("year", 0)))
    return matching


def _format_event_line(ev: dict, parser: LegendsParser) -> str:
    """Format a single artifact event as a human-readable line."""
    year = format_year(ev.get("year"))
    etype = ev.get("type", "unknown event")

    if etype == "artifact created":
        creator = parser.get_hf_name(ev["hfid"]) if ev.get("hfid") else "unknown"
        site = parser.get_site_name(ev["site_id"]) if ev.get("site_id") else "unknown location"
        return f"  Year {year}: Created by {creator} at {site}"

    if etype == "artifact stored":
        site = parser.get_site_name(ev["site_id"]) if ev.get("site_id") else "unknown location"
        return f"  Year {year}: Stored at {site}"

    if etype == "artifact given":
        giver = parser.get_hf_name(ev["giver_hfid"]) if ev.get("giver_hfid") else "unknown"
        receiver = parser.get_hf_name(ev["receiver_hfid"]) if ev.get("receiver_hfid") else "unknown"
        return f"  Year {year}: Given by {giver} to {receiver}"

    if etype == "artifact lost":
        return f"  Year {year}: Lost"

    if etype == "artifact found":
        finder = parser.get_hf_name(ev["hfid"]) if ev.get("hfid") else "unknown"
        site = parser.get_site_name(ev["site_id"]) if ev.get("site_id") else "unknown location"
        return f"  Year {year}: Found by {finder} at {site}"

    if etype == "artifact possessed":
        holder = parser.get_hf_name(ev["hfid"]) if ev.get("hfid") else "unknown"
        return f"  Year {year}: Possessed by {holder}"

    if etype == "artifact recovered":
        recoverer = parser.get_hf_name(ev["hfid"]) if ev.get("hfid") else "unknown"
        site = parser.get_site_name(ev["site_id"]) if ev.get("site_id") else "unknown location"
        return f"  Year {year}: Recovered by {recoverer} at {site}"

    if etype == "artifact claim formed":
        entity = parser.get_entity_name(ev["entity_id"]) if ev.get("entity_id") else "unknown"
        return f"  Year {year}: Claimed by {entity}"

    return f"  Year {year}: {etype}"


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def _filter_artifacts(
    artifacts: dict[str, dict],
    parser: LegendsParser,
    *,
    site: Optional[str] = None,
    holder: Optional[str] = None,
) -> list[dict]:
    """Filter artifacts by site and/or holder criteria."""
    result = list(artifacts.values())

    if site is not None:
        try:
            site_id = parser.resolve_site_id(site)
        except ValueError:
            site_id = site
        result = [a for a in result if str(a.get("site_id", "")) == str(site_id)]

    if holder is not None:
        try:
            holder_id = parser.resolve_hf_id(holder)
        except ValueError:
            holder_id = holder
        result = [a for a in result if str(a.get("holder_hfid", "")) == str(holder_id)]

    return result


# ---------------------------------------------------------------------------
# Output — List Mode
# ---------------------------------------------------------------------------


def _list_artifacts_text(artifacts: list[dict], parser: LegendsParser) -> None:
    """Print a table of artifacts to stdout."""
    if not artifacts:
        print("No artifacts found.")
        return

    # Column headers
    header = f"{'ID':>6}  {'Name':<30}  {'Item Type':<25}  {'Holder':<25}  {'Site':<20}"
    print(header)
    print("-" * len(header))

    for art in sorted(artifacts, key=lambda a: int(a.get("id", 0))):
        aid = art.get("id", "?")
        name = (art.get("name") or "unnamed").title()
        item_type = _get_item_description(art)
        holder_hfid = art.get("holder_hfid")
        holder_name = parser.get_hf_name(holder_hfid) if holder_hfid and holder_hfid != "-1" else "-"
        site_id = art.get("site_id")
        site_name = parser.get_site_name(site_id) if site_id and site_id != "-1" else "-"

        # Truncate long fields to fit table
        name = name[:30]
        item_type = item_type[:25]
        holder_name = holder_name[:25]
        site_name = site_name[:20]

        print(f"{aid:>6}  {name:<30}  {item_type:<25}  {holder_name:<25}  {site_name:<20}")

    print(f"\nTotal: {len(artifacts)} artifact(s)")


def _list_artifacts_json(artifacts: list[dict], parser: LegendsParser) -> None:
    """Output artifacts as JSON."""
    records: list[dict[str, Any]] = []
    for art in sorted(artifacts, key=lambda a: int(a.get("id", 0))):
        holder_hfid = art.get("holder_hfid")
        site_id = art.get("site_id")
        records.append({
            "id": art.get("id"),
            "name": (art.get("name") or "").title(),
            "item_description": _get_item_description(art),
            "holder": parser.get_hf_name(holder_hfid) if holder_hfid and holder_hfid != "-1" else None,
            "holder_hfid": holder_hfid if holder_hfid and holder_hfid != "-1" else None,
            "site": parser.get_site_name(site_id) if site_id and site_id != "-1" else None,
            "site_id": site_id if site_id and site_id != "-1" else None,
        })
    print_json(records)


# ---------------------------------------------------------------------------
# Output — Detail Mode
# ---------------------------------------------------------------------------


def _show_artifact_detail_text(artifact: dict, parser: LegendsParser) -> None:
    """Print detailed information about a single artifact."""
    aid = artifact.get("id", "?")
    name = (artifact.get("name") or "unnamed").title()
    name_string = artifact.get("name_string") or ""
    item_desc = _get_item_description(artifact)

    # --- Artifact identity ---
    print(f"=== {name} ===")
    print(f"  ID: {aid}")
    if name_string:
        print(f"  Full Name: {name_string}")
    print(f"  Item: {item_desc}")

    # --- Location ---
    site_id = artifact.get("site_id")
    structure_id = artifact.get("structure_local_id")
    subregion_id = artifact.get("subregion_id")
    print()
    print("Location:")
    if site_id and site_id != "-1":
        site_name = parser.get_site_name(site_id)
        loc = f"  Site: {site_name} (ID {site_id})"
        if structure_id and structure_id != "-1":
            loc += f", Structure {structure_id}"
        print(loc)
    elif subregion_id and subregion_id != "-1":
        print(f"  Subregion: {subregion_id}")
    else:
        coords = []
        for coord_key in ("abs_tile_x", "abs_tile_y", "abs_tile_z"):
            val = artifact.get(coord_key)
            if val and val != "-1":
                coords.append(f"{coord_key}={val}")
        if coords:
            print(f"  Coordinates: {', '.join(coords)}")
        else:
            print("  Location unknown")

    # --- Current Holder ---
    holder_hfid = artifact.get("holder_hfid")
    print()
    print("Current Holder:")
    if holder_hfid and holder_hfid != "-1":
        hf = parser.hf_map.get(str(holder_hfid))
        if hf:
            print(f"  {format_hf_summary(hf, parser)}")
        else:
            print(f"  HF ID {holder_hfid} (not found in data)")
    else:
        print("  None (no current holder)")

    # --- Creator (from artifact created event) ---
    events = _get_artifact_events(parser, aid)
    created_events = [e for e in events if e.get("type") == "artifact created"]
    print()
    print("Creator:")
    if created_events:
        ev = created_events[0]
        creator = parser.get_hf_name(ev["hfid"]) if ev.get("hfid") else "unknown"
        year = format_year(ev.get("year"))
        site = parser.get_site_name(ev["site_id"]) if ev.get("site_id") else "unknown location"
        print(f"  {creator}, Year {year}, at {site}")
    else:
        print("  Unknown (no creation event recorded)")

    # --- Event History ---
    print()
    print("History:")
    if events:
        for ev in events:
            print(_format_event_line(ev, parser))
    else:
        print("  No recorded events.")


def _show_artifact_detail_json(artifact: dict, parser: LegendsParser) -> None:
    """Output detailed artifact information as JSON."""
    aid = artifact.get("id", "?")
    holder_hfid = artifact.get("holder_hfid")
    site_id = artifact.get("site_id")

    events = _get_artifact_events(parser, aid)
    created_events = [e for e in events if e.get("type") == "artifact created"]

    creator_info: Optional[dict[str, Any]] = None
    if created_events:
        ev = created_events[0]
        creator_info = {
            "hf_name": parser.get_hf_name(ev["hfid"]) if ev.get("hfid") else None,
            "hfid": ev.get("hfid"),
            "year": ev.get("year"),
            "site": parser.get_site_name(ev["site_id"]) if ev.get("site_id") else None,
            "site_id": ev.get("site_id"),
        }

    holder_info: Optional[dict[str, Any]] = None
    if holder_hfid and holder_hfid != "-1":
        hf = parser.hf_map.get(str(holder_hfid))
        holder_info = {
            "hfid": holder_hfid,
            "name": parser.get_hf_name(holder_hfid),
            "summary": format_hf_summary(hf, parser) if hf else None,
        }

    history: list[dict[str, Any]] = []
    for ev in events:
        entry: dict[str, Any] = {
            "year": ev.get("year"),
            "type": ev.get("type"),
            "description": _format_event_line(ev, parser).strip(),
        }
        # Include resolved participant names
        for key in ("hfid", "giver_hfid", "receiver_hfid"):
            if ev.get(key):
                entry[key] = ev[key]
                entry[f"{key}_name"] = parser.get_hf_name(ev[key])
        if ev.get("site_id"):
            entry["site_id"] = ev["site_id"]
            entry["site_name"] = parser.get_site_name(ev["site_id"])
        if ev.get("entity_id"):
            entry["entity_id"] = ev["entity_id"]
            entry["entity_name"] = parser.get_entity_name(ev["entity_id"])
        history.append(entry)

    data: dict[str, Any] = {
        "id": aid,
        "name": (artifact.get("name") or "").title(),
        "name_string": artifact.get("name_string") or None,
        "item_description": _get_item_description(artifact),
        "location": {
            "site": parser.get_site_name(site_id) if site_id and site_id != "-1" else None,
            "site_id": site_id if site_id and site_id != "-1" else None,
            "structure_local_id": artifact.get("structure_local_id"),
            "subregion_id": artifact.get("subregion_id"),
        },
        "holder": holder_info,
        "creator": creator_info,
        "history": history,
    }
    print_json(data)


# ---------------------------------------------------------------------------
# Resolve artifact from name or ID
# ---------------------------------------------------------------------------


def _resolve_artifact(parser: LegendsParser, name_or_id: str) -> dict:
    """Look up an artifact by name or numeric ID.

    Raises:
        SystemExit: If no match or ambiguous match is found.
    """
    # Try numeric ID first
    if name_or_id.isdigit():
        art = parser.artifact_map.get(name_or_id)
        if art:
            return art

    # Name search
    matches = parser.find_artifact_by_name(name_or_id)
    if len(matches) == 0:
        print(f"Error: No artifact found matching '{name_or_id}'.", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        print(f"Multiple artifacts match '{name_or_id}':", file=sys.stderr)
        for m in matches[:15]:
            mid = m.get("id", "?")
            mname = (m.get("name") or "unnamed").title()
            print(f"  [{mid}] {mname}", file=sys.stderr)
        if len(matches) > 15:
            print(f"  ... and {len(matches) - 15} more", file=sys.stderr)
        print("Specify a more precise name or use the numeric ID.", file=sys.stderr)
        sys.exit(1)
    return matches[0]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the artifact script."""
    ap = argparse.ArgumentParser(
        description="Show artifact details from the Dwarf Fortress Legends XML.",
    )
    ap.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Artifact name or numeric ID. If omitted, lists all artifacts.",
    )
    ap.add_argument(
        "--site",
        type=str,
        default=None,
        help="Filter artifacts by site name or ID.",
    )
    ap.add_argument(
        "--holder",
        type=str,
        default=None,
        help="Filter artifacts by holder name or ID.",
    )
    ap.add_argument(
        "--list",
        action="store_true",
        default=False,
        dest="list_mode",
        help="Force list mode even when a name is provided.",
    )
    add_common_args(ap)
    return ap


def main() -> None:
    """Entry point for the artifact CLI."""
    configure_output()
    ap = build_parser()
    args = ap.parse_args()

    with get_parser_from_args(args) as parser:
        # Determine mode: list vs detail
        use_list_mode = args.list_mode or args.name is None

        if use_list_mode:
            # List mode: show matching artifacts
            if args.name:
                # Name provided with --list: filter by name match
                artifacts = parser.find_artifact_by_name(args.name)
            else:
                artifacts = list(parser.artifact_map.values())

            # Apply site/holder filters
            if args.site or args.holder:
                filtered = _filter_artifacts(
                    {a.get("id", ""): a for a in artifacts},
                    parser,
                    site=args.site,
                    holder=args.holder,
                )
                artifacts = filtered

            if args.json:
                _list_artifacts_json(artifacts, parser)
            else:
                _list_artifacts_text(artifacts, parser)

        else:
            # Detail mode: show one artifact
            artifact = _resolve_artifact(parser, args.name)
            if args.json:
                _show_artifact_detail_json(artifact, parser)
            else:
                _show_artifact_detail_text(artifact, parser)


if __name__ == "__main__":
    main()
