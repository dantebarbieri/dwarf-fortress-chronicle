"""
civilization.py — Look up a specific civilization / entity by name or ID
and display its members, wars, sites, and recent events from the Legends XML.

Usage:
    python scripts/civilization.py "guilds of clinching"
    python scripts/civilization.py 42 --members --wars --sites
    python scripts/civilization.py "clinching" --json --year-from 90
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Allow running from the DF root directory:  python scripts/civilization.py …
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.legends_parser import (
    LegendsParser,
    add_common_args,
    configure_output,
    event_involves_entity,
    format_hf_summary,
    format_year,
    get_parser_from_args,
    print_json,
    skill_level_name,
)


# ---------------------------------------------------------------------------
# Display helpers (human-readable)
# ---------------------------------------------------------------------------


def _section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def _print_overview(entity: dict[str, Any]) -> None:
    """Print civilization overview: name, ID, type."""
    _section("Civilization Overview")
    name = (entity.get("name") or "Unnamed").title()
    etype = (entity.get("type") or "unknown").replace("_", " ").title()
    print(f"  Name:  {name}")
    print(f"  ID:    {entity.get('id', '?')}")
    print(f"  Type:  {etype}")


def _get_population_data(
    entity_id: str, parser: LegendsParser
) -> dict[str, Any]:
    """Compute population stats: total, alive/dead, race breakdown."""
    members = parser.get_entity_members(entity_id)
    alive = [m for m in members if format_year(m.get("death_year")) == "present"]
    dead = [m for m in members if m not in alive]
    race_counts: Counter[str] = Counter()
    for m in members:
        race = (m.get("race") or "unknown").replace("_", " ").title()
        race_counts[race] += 1
    return {
        "total": len(members),
        "alive": len(alive),
        "dead": len(dead),
        "by_race": dict(race_counts.most_common()),
    }


def _print_population(entity_id: str, parser: LegendsParser) -> None:
    """Print population summary."""
    data = _get_population_data(entity_id, parser)
    _section(f"Population ({data['total']} members)")
    print(f"  Alive: {data['alive']}    Dead: {data['dead']}")
    if data["by_race"]:
        print("  By race:")
        for race, count in data["by_race"].items():
            print(f"    {race:30s} {count}")


def _get_sites(entity_id: str, parser: LegendsParser) -> list[dict[str, Any]]:
    """Find sites associated with this civilization.

    Sources:
      1. Events of type 'created site' where civ_id matches.
      2. Sites whose entity_id field directly references this civ (if present).
    """
    target = str(entity_id)
    site_ids: set[str] = set()

    # From 'created site' events
    for ev in parser.events:
        if ev.get("type") == "created site" and str(ev.get("civ_id", "")) == target:
            sid = ev.get("site_id")
            if sid:
                site_ids.add(str(sid))

    # From site_map — some sites carry a civ reference directly
    for sid, site in parser.site_map.items():
        if str(site.get("civ_id", "")) == target:
            site_ids.add(sid)

    sites: list[dict[str, Any]] = []
    for sid in sorted(site_ids, key=int):
        site = parser.site_map.get(sid)
        if site:
            sites.append(site)
    return sites


def _print_sites(entity_id: str, parser: LegendsParser) -> None:
    """Print sites owned/created by this civilization."""
    sites = _get_sites(entity_id, parser)
    _section(f"Sites ({len(sites)})")
    if not sites:
        print("  No recorded sites.")
        return
    for site in sites:
        name = (site.get("name") or "unnamed").title()
        stype = (site.get("type") or "?").replace("_", " ").title()
        sid = site.get("id", "?")
        print(f"  {name} (id {sid}) — {stype}")


def _get_notable_members(
    entity_id: str, parser: LegendsParser
) -> list[dict[str, Any]]:
    """Identify notable members: leaders, position holders, most skilled."""
    members = parser.get_entity_members(entity_id)
    target = str(entity_id)
    notables: list[dict[str, Any]] = []

    for hf in members:
        roles: list[str] = []
        # Current positions
        for pos in hf.get("entity_position_links", []):
            if str(pos.get("entity_id", "")) == target:
                roles.append(f"position {pos.get('position_profile_id', '?')} (since yr {pos.get('start_year', '?')})")
        # Former positions
        for pos in hf.get("entity_former_position_links", []):
            if str(pos.get("entity_id", "")) == target:
                roles.append(f"former position {pos.get('position_profile_id', '?')}")
        # Top skill
        skills = hf.get("hf_skills", [])
        top_skill_name = ""
        top_skill_ip = 0
        for sk in skills:
            ip = int(sk.get("total_ip", 0))
            if ip > top_skill_ip:
                top_skill_ip = ip
                top_skill_name = (sk.get("skill") or "?").replace("_", " ").title()

        if roles or top_skill_ip >= 28100:  # Great or above
            notables.append({
                "hf": hf,
                "roles": roles,
                "top_skill": top_skill_name,
                "top_skill_level": skill_level_name(top_skill_ip),
                "top_skill_ip": top_skill_ip,
            })

    # Sort: those with roles first, then by skill IP descending
    notables.sort(key=lambda n: (not n["roles"], -n["top_skill_ip"]))
    return notables


def _print_notable_members(entity_id: str, parser: LegendsParser) -> None:
    """Print notable members: position holders and highly skilled."""
    notables = _get_notable_members(entity_id, parser)
    _section(f"Notable Members ({len(notables)})")
    if not notables:
        print("  No notable members recorded.")
        return
    for n in notables:
        hf = n["hf"]
        summary = format_hf_summary(hf, parser)
        print(f"  {summary}  (id {hf.get('id', '?')})")
        for role in n["roles"]:
            print(f"    └ {role}")
        if n["top_skill"]:
            print(f"    └ top skill: {n['top_skill']} ({n['top_skill_level']})")


def _print_members(entity_id: str, parser: LegendsParser) -> None:
    """Print full member list."""
    members = parser.get_entity_members(entity_id)
    _section(f"All Members ({len(members)})")
    if not members:
        print("  No members recorded.")
        return
    for hf in members:
        print(f"  {format_hf_summary(hf, parser)}  (id {hf.get('id', '?')})")


def _get_wars(
    entity_id: str, parser: LegendsParser
) -> list[dict[str, Any]]:
    """Extract wars from event_collections where civ is aggressor or defender."""
    target = str(entity_id)
    wars: list[dict[str, Any]] = []
    for ec in parser.event_collections:
        if ec.get("type") != "war":
            continue
        aggressor = str(ec.get("aggressor_ent_id", ""))
        defender = str(ec.get("defender_ent_id", ""))
        if aggressor != target and defender != target:
            continue
        role = "aggressor" if aggressor == target else "defender"
        opponent_id = defender if role == "aggressor" else aggressor
        opponent_name = parser.get_entity_name(opponent_id)
        wars.append({
            "name": (ec.get("name") or "unnamed war").title(),
            "id": ec.get("id", "?"),
            "role": role,
            "opponent_id": opponent_id,
            "opponent_name": opponent_name,
            "start_year": ec.get("start_year", "?"),
            "end_year": ec.get("end_year", "?"),
            "event_count": len(ec.get("event", [])) if isinstance(ec.get("event"), list) else (1 if ec.get("event") else 0),
        })
    return wars


def _print_wars(entity_id: str, parser: LegendsParser) -> None:
    """Print war history."""
    wars = _get_wars(entity_id, parser)
    _section(f"Wars ({len(wars)})")
    if not wars:
        print("  No recorded wars.")
        return
    for w in wars:
        end = format_year(w["end_year"])
        print(
            f"  {w['name']} (id {w['id']})"
            f"\n    Role: {w['role']} vs {w['opponent_name']} (id {w['opponent_id']})"
            f"\n    Years {w['start_year']}–{end}   ({w['event_count']} events)"
        )


def _print_events(
    entity_id: str, parser: LegendsParser, args: argparse.Namespace
) -> None:
    """Print chronological event timeline for this civilization."""
    year_from = args.year if args.year else args.year_from
    year_to = args.year if args.year else args.year_to
    events = parser.get_entity_events(entity_id, year_from=year_from, year_to=year_to)
    _section(f"Recent Events ({len(events)} events)")
    if not events:
        print("  No events in range.")
        return
    for ev in events:
        yr = ev.get("year", "?")
        etype = ev.get("type", "?")
        parts: list[str] = [f"[{etype}]"]
        if ev.get("site_id"):
            parts.append(f"site={parser.get_site_name(ev['site_id'])}")
        if ev.get("hfid"):
            parts.append(f"hf={parser.get_hf_name(ev['hfid'])}")
        if ev.get("civ_id") and str(ev["civ_id"]) != str(entity_id):
            parts.append(f"civ={parser.get_entity_name(ev['civ_id'])}")
        print(f"  Year {yr:>5s}  {' '.join(parts)}")


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def _build_json_output(
    entity: dict[str, Any],
    entity_id: str,
    parser: LegendsParser,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Build a JSON-serializable dict with all requested data."""
    data: dict[str, Any] = {"entity": entity}
    data["population"] = _get_population_data(entity_id, parser)

    if args.sites:
        data["sites"] = _get_sites(entity_id, parser)

    data["notable_members"] = [
        {
            "id": n["hf"].get("id"),
            "summary": format_hf_summary(n["hf"], parser),
            "roles": n["roles"],
            "top_skill": n["top_skill"],
            "top_skill_level": n["top_skill_level"],
        }
        for n in _get_notable_members(entity_id, parser)
    ]

    if args.members:
        members = parser.get_entity_members(entity_id)
        data["members"] = [
            {"id": m.get("id"), "summary": format_hf_summary(m, parser)}
            for m in members
        ]

    if args.wars:
        data["wars"] = _get_wars(entity_id, parser)

    year_from = args.year if args.year else args.year_from
    year_to = args.year if args.year else args.year_to
    if year_from is not None or year_to is not None:
        data["events"] = parser.get_entity_events(
            entity_id, year_from=year_from, year_to=year_to
        )

    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for civilization CLI."""
    configure_output()
    ap = argparse.ArgumentParser(
        description="Look up a civilization / entity in the Legends XML.",
    )
    ap.add_argument(
        "name",
        type=str,
        help="Civilization name or numeric ID (partial match allowed).",
    )
    add_common_args(ap)
    ap.add_argument(
        "--members",
        action="store_true",
        default=False,
        help="Show full member list.",
    )
    ap.add_argument(
        "--wars",
        action="store_true",
        default=False,
        help="Show war details.",
    )
    ap.add_argument(
        "--sites",
        action="store_true",
        default=False,
        help="Show sites owned/created by this civilization.",
    )
    args = ap.parse_args()

    with get_parser_from_args(args) as parser:
        # Resolve by ID or name
        try:
            entity_id = parser.resolve_entity_id(args.name)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        entity = parser.entity_map.get(entity_id)
        if not entity:
            print(f"No entity with ID {entity_id}.", file=sys.stderr)
            sys.exit(1)

        # JSON mode
        if args.json:
            print_json(_build_json_output(entity, entity_id, parser, args))
            return

        # Human-readable output
        name = (entity.get("name") or "Unnamed").title()
        print(f"\n{'═' * 60}")
        print(f"  {name}")
        print(f"{'═' * 60}")

        _print_overview(entity)
        _print_population(entity_id, parser)

        if args.sites:
            _print_sites(entity_id, parser)

        _print_notable_members(entity_id, parser)

        if args.members:
            _print_members(entity_id, parser)

        if args.wars:
            _print_wars(entity_id, parser)

        # Show events only when year filters are specified
        year_from = args.year if args.year else args.year_from
        year_to = args.year if args.year else args.year_to
        if year_from is not None or year_to is not None:
            _print_events(entity_id, parser, args)

        print()


if __name__ == "__main__":
    main()
