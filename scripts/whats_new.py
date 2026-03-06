"""
whats_new.py — "What changed since year N" for Dwarf Fortress Legends XML.

Shows all events from a given year onward, grouped by year and season,
categorized by type (arrivals, deaths, artifacts, wars, trade, diplomacy,
construction, other).  Designed as the opening move for every chronicle
update session.

Usage examples:
    python scripts/whats_new.py --since-year 101
    python scripts/whats_new.py --since-year 100 --site luregold
    python scripts/whats_new.py --since-year 100 --entity "guilds of clinching" --json
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
    event_involves_entity,
    event_involves_site,
    format_year,
    get_parser_from_args,
    print_json,
)
from scripts.events import describe_event


# ---------------------------------------------------------------------------
# Season classification
# ---------------------------------------------------------------------------

_SEASON_RANGES: list[tuple[str, int, int]] = [
    ("Spring", 0, 100800),
    ("Summer", 100801, 201600),
    ("Autumn", 201601, 302400),
    ("Winter", 302401, 999999999),
]


def _season_name(seconds72: int) -> str:
    """Map a seconds72 value to a season name."""
    for name, lo, hi in _SEASON_RANGES:
        if lo <= seconds72 <= hi:
            return name
    return "Unknown"


# ---------------------------------------------------------------------------
# Event categorization
# ---------------------------------------------------------------------------

_CATEGORY_ORDER = [
    "Arrivals",
    "Deaths",
    "Artifacts",
    "Wars/Battles",
    "Trade",
    "Diplomacy",
    "Construction",
    "Other",
]

# Event types that map to war/battle collections
_WAR_BATTLE_TYPES = frozenset({
    "hf simple battle event",
    "hf attacked site",
    "hf destroyed site",
    "site dispute",
    "attacked site",
    "destroyed site",
    "field battle",
    "body abused",
    "hf wounded",
    "creature devoured",
    "tactical situation",
})


def _build_collection_event_ids(parser: LegendsParser) -> frozenset[str]:
    """Return the set of event IDs that belong to war/battle collections."""
    ids: set[str] = set()
    for col in parser.event_collections:
        ctype = col.get("type", "")
        if ctype in ("war", "battle", "site conquered", "abduction",
                      "beast attack", "raid", "destruction"):
            for eid in col.get("events", []):
                ids.add(str(eid))
    return frozenset(ids)


def categorize_event(
    ev: dict,
    collection_event_ids: frozenset[str],
) -> str:
    """Assign a category string to an event."""
    etype = ev.get("type", "")
    eid = str(ev.get("id", ""))

    # Arrivals: change hf state where state=settled
    if etype == "change hf state" and ev.get("state") == "settled":
        return "Arrivals"

    # Deaths
    if etype == "hf died":
        return "Deaths"

    # Artifacts
    if etype in ("artifact created", "masterpiece item",
                 "artifact stored", "artifact possessed",
                 "artifact lost", "artifact found"):
        return "Artifacts"

    # Wars/Battles — explicit types or membership in a war/battle collection
    if etype in _WAR_BATTLE_TYPES or eid in collection_event_ids:
        return "Wars/Battles"

    # Trade
    if etype == "merchant":
        return "Trade"

    # Diplomacy
    if etype == "add hf entity link" and ev.get("link_type") == "position":
        return "Diplomacy"

    # Construction
    if etype in ("created site", "created structure",
                 "reclaim site", "site taken over"):
        return "Construction"

    return "Other"


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------

def _season_sort_key(season: str) -> int:
    """Return an integer for sorting seasons chronologically."""
    order = {"Spring": 0, "Summer": 1, "Autumn": 2, "Winter": 3}
    return order.get(season, 4)


def group_events(
    events: list[dict],
    parser: LegendsParser,
) -> dict[int, dict[str, dict[str, list[dict]]]]:
    """Group events by year → season → category.

    Returns::

        {
            year: {
                "Spring": {"Deaths": [ev, ...], "Arrivals": [ev, ...], ...},
                "Summer": {...},
                ...
            },
            ...
        }
    """
    collection_event_ids = _build_collection_event_ids(parser)

    result: dict[int, dict[str, dict[str, list[dict]]]] = {}
    for ev in events:
        try:
            year = int(ev.get("year", -1))
        except (ValueError, TypeError):
            year = -1
        s72 = int(ev.get("seconds72", 0) or 0)
        season = _season_name(s72)
        cat = categorize_event(ev, collection_event_ids)

        result.setdefault(year, {}).setdefault(season, {}).setdefault(cat, []).append(ev)

    return result


# ---------------------------------------------------------------------------
# Output — human-readable
# ---------------------------------------------------------------------------

def print_grouped(
    grouped: dict[int, dict[str, dict[str, list[dict]]]],
    parser: LegendsParser,
) -> None:
    """Print year → season → category → events in readable form."""
    if not grouped:
        print("No events found for the specified period.")
        return

    total = sum(
        len(evs)
        for seasons in grouped.values()
        for cats in seasons.values()
        for evs in cats.values()
    )
    print(f"=== What's New: {total} events ===\n")

    for year in sorted(grouped):
        year_label = format_year(str(year)) if year >= 0 else "Unknown"
        print(f"--- Year {year_label} ---")

        seasons = grouped[year]
        for season in sorted(seasons, key=_season_sort_key):
            categories = seasons[season]
            ev_count = sum(len(evs) for evs in categories.values())
            print(f"\n  {season} ({ev_count} events)")

            for cat in _CATEGORY_ORDER:
                evs = categories.get(cat)
                if not evs:
                    continue
                print(f"    [{cat}] ({len(evs)})")
                for ev in evs:
                    desc = describe_event(ev, parser)
                    eid = ev.get("id", "?")
                    print(f"      #{eid}: {desc}")
        print()


# ---------------------------------------------------------------------------
# Output — JSON
# ---------------------------------------------------------------------------

def build_json_output(
    grouped: dict[int, dict[str, dict[str, list[dict]]]],
    parser: LegendsParser,
) -> list[dict[str, Any]]:
    """Build a JSON-serializable list from the grouped structure."""
    result: list[dict[str, Any]] = []
    for year in sorted(grouped):
        year_entry: dict[str, Any] = {"year": year, "seasons": []}
        seasons = grouped[year]
        for season in sorted(seasons, key=_season_sort_key):
            categories = seasons[season]
            season_entry: dict[str, Any] = {"season": season, "categories": []}
            for cat in _CATEGORY_ORDER:
                evs = categories.get(cat)
                if not evs:
                    continue
                cat_entry: dict[str, Any] = {
                    "category": cat,
                    "count": len(evs),
                    "events": [],
                }
                for ev in evs:
                    cat_entry["events"].append({
                        **ev,
                        "description": describe_event(ev, parser),
                    })
                season_entry["categories"].append(cat_entry)
            year_entry["seasons"].append(season_entry)
        result.append(year_entry)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    ap = argparse.ArgumentParser(
        description=(
            "Show what changed since a given year in Dwarf Fortress "
            "Legends XML, grouped by year/season and categorized."
        ),
    )
    add_common_args(ap)

    ap.add_argument(
        "--since-year", type=int, required=True,
        help="Show events from this year onward (required).",
    )
    ap.add_argument(
        "--site", type=str, default=None,
        help="Filter to events at this site (name or ID).",
    )
    ap.add_argument(
        "--entity", type=str, default=None,
        help="Filter to events involving this entity (name or ID).",
    )
    return ap


def main() -> None:
    """Entry point."""
    configure_output()
    ap = build_parser()
    args = ap.parse_args()

    with get_parser_from_args(args) as parser:
        # Resolve names to IDs
        site_id: str | None = None
        entity_id: str | None = None

        if args.site:
            site_id = parser.resolve_site_id(args.site)
        if args.entity:
            entity_id = parser.resolve_entity_id(args.entity)

        # Filter events from since_year onward
        events = parser.filter_events(
            year_from=args.since_year,
            site_id=site_id,
            entity_id=entity_id,
        )

        # Group and output
        grouped = group_events(events, parser)

        if args.json:
            print_json(build_json_output(grouped, parser))
        else:
            print_grouped(grouped, parser)


if __name__ == "__main__":
    main()
