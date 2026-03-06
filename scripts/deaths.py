"""
deaths.py — Death/obituary tracker for Dwarf Fortress Legends XML.

Tracks who died, how, when, and by whose hand.  Powers Atir's "reckoning
of the dead" chronicle sections.

Usage examples:
    python scripts/deaths.py --year 101
    python scripts/deaths.py --year-from 100 --year-to 102 --site testfort
    python scripts/deaths.py --entity "the guilds of clinching" --year 101 --json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Ensure the DF root is on sys.path so ``from scripts.legends_parser …`` works
# when the script is invoked directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.legends_parser import (
    LegendsParser,
    add_common_args,
    configure_output,
    format_year,
    get_parser_from_args,
    print_json,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MEMBER_LINK_TYPES = frozenset({
    "member", "position", "former member", "former position",
    "mercenary", "prisoner", "slave", "squad",
})


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _hf_is_member(hf: dict, entity_id: str) -> bool:
    """Return True if *hf* is (or was) a member of *entity_id*."""
    target = str(entity_id)
    for link in hf.get("entity_links", []):
        if (
            str(link.get("entity_id")) == target
            and link.get("link_type") in _MEMBER_LINK_TYPES
        ):
            return True
    return False


def _calc_age(hf: dict, death_year: int) -> int | None:
    """Calculate age at death from birth_year and the event's year."""
    try:
        birth = int(hf.get("birth_year", -1))
    except (ValueError, TypeError):
        return None
    if birth < -9999:
        return None
    return death_year - birth


def _is_notable(hf: dict) -> bool:
    """Flag a figure as notable if they held positions or had high skills."""
    if hf.get("entity_position_links"):
        return True
    for skill in hf.get("hf_skills", []):
        try:
            if int(skill.get("total_ip", 0)) >= 12800:  # Professional+
                return True
        except (ValueError, TypeError):
            pass
    return False


def build_death_record(
    event: dict,
    parser: LegendsParser,
    *,
    entity_id: str | None = None,
) -> dict[str, Any] | None:
    """Build a structured death record from an ``hf died`` event.

    Returns *None* if the event doesn't match optional *entity_id* filter.
    """
    hfid = event.get("hfid")
    if not hfid or hfid == "-1":
        return None

    hf = parser.hf_map.get(str(hfid))
    if not hf:
        return None

    # Entity membership filter
    if entity_id and not _hf_is_member(hf, entity_id):
        return None

    try:
        death_year = int(event.get("year", -1))
    except (ValueError, TypeError):
        death_year = -1

    # Dead HF info
    name = (hf.get("name") or "unnamed").title()
    race = (hf.get("race") or "UNKNOWN").upper()
    caste = (hf.get("caste") or "").lower()
    profession = (hf.get("associated_type") or "").replace("_", " ").title() or None
    age = _calc_age(hf, death_year)

    # Slayer info
    slayer_hfid = event.get("slayer_hfid")
    slayer_info: dict[str, Any] | None = None
    if slayer_hfid and slayer_hfid != "-1":
        slayer_hf = parser.hf_map.get(str(slayer_hfid))
        if slayer_hf:
            slayer_info = {
                "id": str(slayer_hf["id"]),
                "name": (slayer_hf.get("name") or "unnamed").title(),
                "race": (slayer_hf.get("race") or "UNKNOWN").upper(),
                "caste": (slayer_hf.get("caste") or "").lower(),
            }
        else:
            # Fallback to event-level slayer race/caste
            slayer_info = {
                "id": slayer_hfid,
                "name": "Unknown",
                "race": (event.get("slayer_race") or "UNKNOWN").upper(),
                "caste": (event.get("slayer_caste") or "").lower(),
            }

    # Location
    site_id = event.get("site_id")
    site_name: str | None = None
    if site_id and site_id != "-1":
        site_name = parser.get_site_name(str(site_id)).lower()

    # Entity memberships
    entities: list[str] = []
    for link in hf.get("entity_links", []):
        if link.get("link_type") in _MEMBER_LINK_TYPES:
            eid = str(link.get("entity_id", ""))
            ent_name = parser.get_entity_name(eid)
            entities.append(ent_name.lower())

    cause = event.get("cause", "unknown")

    return {
        "event_id": str(event.get("id", "")),
        "year": death_year,
        "seconds72": event.get("seconds72"),
        "hfid": str(hfid),
        "name": name,
        "race": race,
        "caste": caste,
        "profession": profession,
        "age": age,
        "cause": cause,
        "slayer": slayer_info,
        "site": site_name,
        "site_id": site_id,
        "entities": entities,
        "notable": _is_notable(hf),
    }


def collect_deaths(
    parser: LegendsParser,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    site_id: str | None = None,
    entity_id: str | None = None,
    hf_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return a sorted list of death records matching the given filters."""
    events = parser.filter_events(
        year_from=year_from,
        year_to=year_to,
        event_type="hf died",
        site_id=site_id,
        hf_id=hf_id,
    )

    deaths: list[dict[str, Any]] = []
    for ev in events:
        rec = build_death_record(ev, parser, entity_id=entity_id)
        if rec is not None:
            deaths.append(rec)

    # Chronological sort: year, then seconds72
    deaths.sort(key=lambda d: (d["year"], d.get("seconds72") or 0))
    return deaths


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------

def _format_season(seconds72: Any) -> str:
    """Convert seconds72 to an approximate season label."""
    try:
        s = int(seconds72)
    except (ValueError, TypeError):
        return ""
    # DF year = 403200 seconds72; each season ~100800
    if s < 100800:
        return "Early Spring"
    elif s < 201600:
        return "Late Spring"
    elif s < 302400:
        return "Early Autumn"
    else:
        return "Late Autumn"


def print_deaths(deaths: list[dict[str, Any]], year_from: int | None, year_to: int | None) -> None:
    """Print death records in human-readable format."""
    # Header
    if year_from is not None and year_to is not None and year_from == year_to:
        print(f"Deaths: Year {year_from}")
        print("=" * (len(f"Deaths: Year {year_from}")))
    elif year_from is not None or year_to is not None:
        fr = format_year(year_from) if year_from is not None else "?"
        to = format_year(year_to) if year_to is not None else "?"
        title = f"Deaths: Years {fr}–{to}"
        print(title)
        print("=" * len(title))
    else:
        print("Deaths")
        print("=" * 6)

    if not deaths:
        print("\nNo deaths found in the given range.")
        print(f"\n--- 0 death(s) ---")
        return

    print()
    for rec in deaths:
        season = _format_season(rec.get("seconds72"))
        year_label = f"Year {rec['year']}"
        if season:
            year_label += f", {season}"
        print(f"{year_label}:")

        # Name line
        parts = [f"  {rec['name']} ({rec['race']}"]
        if rec["caste"]:
            parts[0] += f", {rec['caste']}"
        if rec["age"] is not None:
            parts[0] += f", age {rec['age']}"
        parts[0] += ")"
        if rec["notable"]:
            parts[0] += " [NOTABLE]"
        print(parts[0])

        # Cause
        print(f"    Cause: {rec['cause']}")

        # Slayer
        if rec["slayer"]:
            sl = rec["slayer"]
            slayer_desc = f"{sl['name']} ({sl['race']}"
            if sl["caste"]:
                slayer_desc += f", {sl['caste']}"
            slayer_desc += ")"
            print(f"    Slayer: {slayer_desc}")

        # Location
        if rec["site"]:
            print(f"    Location: {rec['site']}")

        # Entity membership
        if rec["entities"]:
            print(f"    Entity: {', '.join(rec['entities'])}")

        print()

    print(f"--- {len(deaths)} death(s)", end="")
    if year_from is not None and year_to is not None and year_from == year_to:
        print(f" in year {year_from}", end="")
    elif year_from is not None or year_to is not None:
        fr = format_year(year_from) if year_from is not None else "?"
        to = format_year(year_to) if year_to is not None else "?"
        print(f" in years {fr}–{to}", end="")
    print(" ---")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    ap = argparse.ArgumentParser(
        description="Track deaths in Dwarf Fortress Legends XML — "
        "who died, how, when, and by whose hand.",
    )
    add_common_args(ap)

    ap.add_argument(
        "--site", type=str, default=None,
        help="Filter to deaths at this site (name or ID).",
    )
    ap.add_argument(
        "--entity", type=str, default=None,
        help="Filter to deaths of members of this entity (name or ID).",
    )
    ap.add_argument(
        "--figure", type=str, default=None,
        help="Filter to a specific figure's death (name or ID).",
    )
    return ap


def main() -> None:
    """Entry point."""
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
        entity_id: str | None = None
        hf_id: str | None = None

        if args.site:
            site_id = parser.resolve_site_id(args.site)
        if args.entity:
            entity_id = parser.resolve_entity_id(args.entity)
        if args.figure:
            hf_id = parser.resolve_hf_id(args.figure)

        deaths = collect_deaths(
            parser,
            year_from=year_from,
            year_to=year_to,
            site_id=site_id,
            entity_id=entity_id,
            hf_id=hf_id,
        )

        if args.json:
            print_json(deaths)
            return

        print_deaths(deaths, year_from, year_to)


if __name__ == "__main__":
    main()
