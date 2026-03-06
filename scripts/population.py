"""
population.py — Population census tracker for Dwarf Fortress Legends XML.

Tracks population changes at a site over time by analysing settlement
arrivals (``change hf state`` with ``state=settled``), deaths
(``hf died``), and departures (state changes away from settled).
Computes running totals year by year with optional race breakdown.

Usage examples:
    python scripts/population.py testfort
    python scripts/population.py testfort --year-from 99 --year-to 102
    python scripts/population.py testfort --by-race --json
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Ensure the DF root is on sys.path so ``from scripts.legends_parser …`` works
# when the script is invoked directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.legends_parser import (
    LegendsParser,
    add_common_args,
    configure_output,
    get_parser_from_args,
    print_json,
)

# States that indicate departure from a site.
_DEPARTURE_STATES = frozenset({"wandering", "visiting", "scouting", "snatcher", "hunting"})


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _collect_population_events(
    parser: LegendsParser,
    site_id: str,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict[str, Any]:
    """Collect arrival, death, and departure events at *site_id*.

    Returns a dict with ``arrivals``, ``deaths``, and ``departures`` each
    mapping year (int) → list of HF dicts (with id, name, race).
    Also returns ``years`` — sorted list of all years with activity.
    """
    arrivals: dict[int, list[dict]] = defaultdict(list)
    deaths: dict[int, list[dict]] = defaultdict(list)
    departures: dict[int, list[dict]] = defaultdict(list)

    sid = str(site_id)

    # Track who has settled at the site so we only count deaths/departures
    # for figures who are actually part of the population.
    settled_hfids: set[str] = set()

    for ev in parser.events:
        ev_year_str = ev.get("year")
        if ev_year_str is None:
            continue
        try:
            ev_year = int(ev_year_str)
        except (ValueError, TypeError):
            continue

        ev_type = ev.get("type", "")
        ev_site = str(ev.get("site_id", ""))

        if ev_site != sid:
            continue

        hfid = ev.get("hfid")
        if not hfid or hfid == "-1":
            continue

        hfid_str = str(hfid)

        if ev_type == "change hf state":
            state = (ev.get("state") or "").lower()
            if state == "settled":
                settled_hfids.add(hfid_str)
                hf = parser.hf_map.get(hfid_str, {})
                arrivals[ev_year].append({
                    "id": hfid_str,
                    "name": (hf.get("name") or "Unknown").title(),
                    "race": (hf.get("race") or "UNKNOWN").upper(),
                })
            elif state in _DEPARTURE_STATES and hfid_str in settled_hfids:
                settled_hfids.discard(hfid_str)
                hf = parser.hf_map.get(hfid_str, {})
                departures[ev_year].append({
                    "id": hfid_str,
                    "name": (hf.get("name") or "Unknown").title(),
                    "race": (hf.get("race") or "UNKNOWN").upper(),
                })

        elif ev_type == "hf died" and hfid_str in settled_hfids:
            settled_hfids.discard(hfid_str)
            hf = parser.hf_map.get(hfid_str, {})
            deaths[ev_year].append({
                "id": hfid_str,
                "name": (hf.get("name") or "Unknown").title(),
                "race": (hf.get("race") or "UNKNOWN").upper(),
            })

    # Determine year range
    all_years = set(arrivals) | set(deaths) | set(departures)
    if not all_years:
        return {
            "arrivals": arrivals,
            "deaths": deaths,
            "departures": departures,
            "years": [],
        }

    min_year = min(all_years)
    max_year = max(all_years)

    if year_from is not None:
        min_year = max(min_year, year_from)
    if year_to is not None:
        max_year = min(max_year, year_to)

    years = list(range(min_year, max_year + 1))

    return {
        "arrivals": arrivals,
        "deaths": deaths,
        "departures": departures,
        "years": years,
    }


def build_population_census(
    parser: LegendsParser,
    site_id: str,
    year_from: int | None = None,
    year_to: int | None = None,
    by_race: bool = False,
) -> dict[str, Any]:
    """Build a full population census for the given site.

    Returns a dict suitable for JSON serialization or text display.
    """
    data = _collect_population_events(parser, site_id, year_from, year_to)
    arrivals = data["arrivals"]
    deaths = data["deaths"]
    departures = data["departures"]
    years = data["years"]

    # Walk all years (including before the visible range) to compute the
    # correct starting population.
    all_event_years = set(arrivals) | set(deaths) | set(departures)
    global_min = min(all_event_years) if all_event_years else 0

    # Compute population before the visible window.
    population = 0
    race_counts: dict[str, int] = defaultdict(int)

    if years:
        display_start = years[0]
    else:
        display_start = year_from if year_from is not None else 0

    for y in range(global_min, display_start):
        for hf in arrivals.get(y, []):
            population += 1
            race_counts[hf["race"]] += 1
        for hf in deaths.get(y, []):
            population -= 1
            race_counts[hf["race"]] -= 1
        for hf in departures.get(y, []):
            population -= 1
            race_counts[hf["race"]] -= 1

    # Build per-year records
    year_records: list[dict[str, Any]] = []
    for y in years:
        yr_arrivals = arrivals.get(y, [])
        yr_deaths = deaths.get(y, [])
        yr_departures = departures.get(y, [])

        for hf in yr_arrivals:
            population += 1
            race_counts[hf["race"]] += 1
        for hf in yr_deaths:
            population -= 1
            race_counts[hf["race"]] -= 1
        for hf in yr_departures:
            population -= 1
            race_counts[hf["race"]] -= 1

        record: dict[str, Any] = {
            "year": y,
            "arrived": len(yr_arrivals),
            "arrived_names": [h["name"] for h in yr_arrivals],
            "died": len(yr_deaths),
            "died_names": [h["name"] for h in yr_deaths],
            "departed": len(yr_departures),
            "departed_names": [h["name"] for h in yr_departures],
            "end_population": population,
        }
        year_records.append(record)

    # Resolve site name
    site = parser.site_map.get(str(site_id), {})
    site_name = (site.get("name") or "Unknown").title()

    result: dict[str, Any] = {
        "site_id": str(site_id),
        "site_name": site_name,
        "years": year_records,
        "current_population": population,
    }

    if by_race:
        result["by_race"] = {
            race: count for race, count in sorted(race_counts.items())
            if count > 0
        }

    return result


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------

def print_census(census: dict[str, Any]) -> None:
    """Print a human-readable population census."""
    site_name = census["site_name"]
    print(f"Population at {site_name}")
    print("=" * (len(f"Population at {site_name}")))

    for yr in census["years"]:
        print()
        print(f"Year {yr['year']}:")

        arrived = yr["arrived"]
        names = yr.get("arrived_names", [])
        if names:
            print(f"  Arrived: {arrived} ({', '.join(names)})")
        else:
            print(f"  Arrived: {arrived}")

        died = yr["died"]
        died_names = yr.get("died_names", [])
        if died_names:
            print(f"  Died:    {died} ({', '.join(died_names)})")
        else:
            print(f"  Died:    {died}")

        departed = yr["departed"]
        departed_names = yr.get("departed_names", [])
        if departed > 0:
            if departed_names:
                print(f"  Left:    {departed} ({', '.join(departed_names)})")
            else:
                print(f"  Left:    {departed}")

        print(f"  End:     {yr['end_population']}")

    print()
    print(f"--- Current population: {census['current_population']} ---")

    if "by_race" in census:
        print()
        for race, count in sorted(census["by_race"].items()):
            print(f"  {race}: {count}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_argparser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    ap = argparse.ArgumentParser(
        description="Track population changes at a Dwarf Fortress site over time.",
    )
    add_common_args(ap)

    ap.add_argument(
        "name",
        help="Site name or numeric ID.",
    )
    ap.add_argument(
        "--by-race", action="store_true", default=False,
        help="Break down population by race.",
    )
    return ap


def main() -> None:
    """Entry point."""
    configure_output()
    ap = build_argparser()
    args = ap.parse_args()

    # Normalise year args
    year_from: int | None = args.year if args.year else args.year_from
    year_to: int | None = args.year if args.year else args.year_to

    with get_parser_from_args(args) as parser:
        # Resolve the site
        try:
            site_id = parser.resolve_site_id(args.name)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)

        # Verify it actually exists in the site map
        if site_id not in parser.site_map and not args.name.isdigit():
            print(f"No site found matching '{args.name}'.", file=sys.stderr)
            sys.exit(1)

        census = build_population_census(
            parser,
            site_id,
            year_from=year_from,
            year_to=year_to,
            by_race=args.by_race,
        )

        if args.json:
            print_json(census)
        else:
            print_census(census)


if __name__ == "__main__":
    main()
