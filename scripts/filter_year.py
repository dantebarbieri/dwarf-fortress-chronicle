"""
filter_year.py — Filter Dwarf Fortress Legends XML events by year or year range.

Usage from the DF root directory:
    python scripts/filter_year.py --year 102
    python scripts/filter_year.py --year-from 100 --year-to 102 --site luregold
    python scripts/filter_year.py --year 101 --type "hf died" --summary
    python scripts/filter_year.py --year-from 100 --year-to 102 --figure "urist" --json
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

# Ensure the DF root is on sys.path so ``from scripts.legends_parser`` works
# when invoked as ``python scripts/filter_year.py`` from the DF root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.legends_parser import (
    LegendsParser,
    add_common_args,
    configure_output,
    format_year,
    get_parser_from_args,
    print_json,
)

# -- HF / entity / site field names used to resolve participants ----------

_HF_FIELDS: list[str] = [
    "hfid", "hfid1", "hfid2", "slayer_hfid", "group_hfid",
    "attacker_hfid", "defender_hfid", "trickster_hfid", "target_hfid",
    "changee_hfid", "changer_hfid", "doer_hfid", "histfig_id",
    "hist_figure_id", "holder_hfid", "builder_hfid", "maker_hfid",
    "acquirer_hfid", "a_hfid", "d_hfid", "woundee_hfid", "wounder_hfid",
    "seeker_hfid", "snatcher_hfid", "corruptor_hfid",
]

_ENTITY_FIELDS: list[str] = [
    "civ_id", "entity_id", "attacker_civ_id", "defender_civ_id",
    "site_civ_id", "target_entity_id", "source_entity_id",
]

_SITE_FIELDS: list[str] = [
    "site_id", "site_id1", "site_id2",
]


# -- Formatting helpers ----------------------------------------------------

def _resolve_participants(event: dict, parser: LegendsParser) -> str:
    """Build a human-readable string of key participants in *event*."""
    parts: list[str] = []

    for field in _HF_FIELDS:
        val = event.get(field)
        if val and str(val) != "-1":
            name = parser.get_hf_name(str(val))
            if name and not name.startswith("Unknown"):
                label = field.replace("_hfid", "").replace("_id", "").replace("hfid", "subject")
                parts.append(f"{label}={name}")

    for field in _ENTITY_FIELDS:
        val = event.get(field)
        if val and str(val) != "-1":
            name = parser.get_entity_name(str(val))
            if name and not name.startswith("Unknown"):
                label = field.replace("_id", "").replace("civ", "civ")
                parts.append(f"{label}={name}")

    for field in _SITE_FIELDS:
        val = event.get(field)
        if val and str(val) != "-1":
            name = parser.get_site_name(str(val))
            if name and not name.startswith("Unknown"):
                label = field.replace("_id", "").replace("site", "site")
                parts.append(f"{label}={name}")

    return ", ".join(parts)


def _format_event_line(event: dict, parser: LegendsParser) -> str:
    """Format a single event as a one-line human-readable string."""
    year = format_year(event.get("year"))
    seconds = event.get("seconds72", "")
    time_str = f"Year {year}" + (f".{seconds}" if seconds and seconds != "-1" else "")

    etype = event.get("type", "unknown")
    participants = _resolve_participants(event, parser)

    line = f"  {time_str}: {etype}"
    if participants:
        line += f" — {participants}"
    return line


def _print_summary(events: list[dict]) -> None:
    """Print a count-by-type summary table, sorted by count descending."""
    counts: Counter[str] = Counter(ev.get("type", "unknown") for ev in events)
    if not counts:
        print("  (no events)")
        return

    # Column widths
    max_type_len = max(len(t) for t in counts)
    max_count_len = max(len(str(c)) for c in counts.values())

    print(f"  {'Event Type':<{max_type_len}}  {'Count':>{max_count_len}}")
    print(f"  {'-' * max_type_len}  {'-' * max_count_len}")
    for etype, count in counts.most_common():
        print(f"  {etype:<{max_type_len}}  {count:>{max_count_len}}")
    print()
    print(f"  Total: {len(events)} events across {len(counts)} types")


def _build_header(args: argparse.Namespace) -> str:
    """Build the output header line describing the year filter."""
    if args.year is not None:
        return f"Events for Year {args.year}"
    parts: list[str] = []
    if args.year_from is not None:
        parts.append(f"from Year {args.year_from}")
    if args.year_to is not None:
        parts.append(f"to Year {args.year_to}")
    return "Events " + " ".join(parts)


def _build_filter_description(args: argparse.Namespace) -> list[str]:
    """Return a list of human-readable active-filter descriptions."""
    filters: list[str] = []
    if getattr(args, "type", None):
        filters.append(f"type = {args.type}")
    if getattr(args, "site", None):
        filters.append(f"site = {args.site}")
    if getattr(args, "entity", None):
        filters.append(f"entity = {args.entity}")
    if getattr(args, "figure", None):
        filters.append(f"figure = {args.figure}")
    if getattr(args, "limit", None):
        filters.append(f"limit = {args.limit}")
    return filters


# -- Main ------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> None:
    """Entry point for the filter-year script."""
    configure_output()
    ap = argparse.ArgumentParser(
        description="Filter Legends XML events by year or year range.",
    )
    add_common_args(ap)  # --xml, --year, --year-from, --year-to, --json

    ap.add_argument("--type", type=str, default=None, help="Filter by event type string.")
    ap.add_argument("--site", type=str, default=None, help="Filter by site name or ID.")
    ap.add_argument("--entity", type=str, default=None, help="Filter by entity name or ID.")
    ap.add_argument("--figure", type=str, default=None, help="Filter by historical figure name or ID.")
    ap.add_argument("--summary", action="store_true", default=False, help="Show count-by-type summary instead of event list.")
    ap.add_argument("--limit", type=int, default=None, help="Limit number of events shown.")

    args = ap.parse_args(argv)

    # Validate: at least one year filter is required
    if args.year is None and args.year_from is None and args.year_to is None:
        ap.error("At least one of --year, --year-from, or --year-to is required.")

    # Determine year range
    if args.year is not None:
        year_from: int | None = args.year
        year_to: int | None = args.year
    else:
        year_from = args.year_from
        year_to = args.year_to

    # Load parser
    parser = get_parser_from_args(args)

    # Resolve name-based filters to IDs
    site_id: str | None = None
    entity_id: str | None = None
    hf_id: str | None = None

    if args.site:
        site_id = parser.resolve_site_id(args.site)
    if args.entity:
        entity_id = parser.resolve_entity_id(args.entity)
    if args.figure:
        hf_id = parser.resolve_hf_id(args.figure)

    # Filter events
    events = parser.filter_events(
        year_from=year_from,
        year_to=year_to,
        event_type=args.type,
        site_id=site_id,
        entity_id=entity_id,
        hf_id=hf_id,
    )

    # Apply limit
    limited = False
    total_count = len(events)
    if args.limit is not None and args.limit < len(events):
        events = events[: args.limit]
        limited = True

    # JSON output
    if args.json:
        print_json(events)
        return

    # Human-readable output
    header = _build_header(args)
    print(f"\n{header}")
    print("=" * len(header))

    active_filters = _build_filter_description(args)
    if active_filters:
        print(f"Filters: {', '.join(active_filters)}")

    print(f"Found {total_count} event(s).\n")

    if args.summary:
        # Use the full set for summary counts even when limited
        _print_summary(events)
    else:
        for ev in events:
            print(_format_event_line(ev, parser))
        if limited:
            print(f"\n  ... showing {len(events)} of {total_count} events (--limit {args.limit})")

    print()


if __name__ == "__main__":
    main()
