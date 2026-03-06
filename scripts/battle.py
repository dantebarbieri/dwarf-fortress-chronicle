"""
battle.py — Battle and war analysis from Dwarf Fortress Legends XML.

Provides subcommands for listing wars, battles, and showing detailed
information about specific event collections (wars, battles, duels, etc.).

Usage:
    python scripts/battle.py wars
    python scripts/battle.py wars --entity "guilds of clinching"
    python scripts/battle.py battles --year 102
    python scripts/battle.py detail 1234
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Ensure the DF root is on sys.path so `scripts.legends_parser` resolves.
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
# Helpers
# ---------------------------------------------------------------------------

def _ensure_list(val: Any) -> list[str]:
    """Normalise a value that may be a string, list, or None into a list."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def _int_or_zero(val: Any) -> int:
    """Coerce *val* to int, returning 0 on failure."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _build_ec_map(parser: LegendsParser) -> dict[str, dict]:
    """Build event-collection lookup keyed by ID."""
    return {str(ec["id"]): ec for ec in parser.event_collections if "id" in ec}


def _build_event_map(parser: LegendsParser) -> dict[str, dict]:
    """Build event lookup keyed by ID."""
    return {str(ev["id"]): ev for ev in parser.events if "id" in ev}


def _collection_involves_entity(ec: dict, entity_id: str) -> bool:
    """Return True if *ec* references *entity_id* as participant."""
    eid = str(entity_id)
    for field in (
        "aggressor_ent_id", "defender_ent_id",
        "attacking_enid", "defending_enid",
        "attacking_merc_enid", "defending_merc_enid",
        "entity_id", "civ_id",
    ):
        val = ec.get(field)
        if val is None:
            continue
        if isinstance(val, list):
            if eid in val:
                return True
        elif str(val) == eid:
            return True
    return False


def _collection_involves_site(ec: dict, site_id: str) -> bool:
    """Return True if *ec* references *site_id*."""
    sid = str(site_id)
    for field in ("site_id", "subregion_id"):
        val = ec.get(field)
        if val is not None and str(val) == sid:
            return True
    return False


def _format_year_range(ec: dict) -> str:
    """Format the start→end year range for a collection."""
    start = format_year(ec.get("start_year"))
    end_raw = ec.get("end_year")
    end = "ongoing" if str(end_raw).strip() in ("-1", "") else format_year(end_raw)
    return f"{start} → {end}"


def _is_ongoing(ec: dict) -> bool:
    """Return True if the collection's end_year indicates it is still active."""
    return str(ec.get("end_year", "")).strip() in ("-1", "")


# ---------------------------------------------------------------------------
# Wars subcommand
# ---------------------------------------------------------------------------

def cmd_wars(args: argparse.Namespace) -> None:
    """List wars from the Legends XML."""
    parser = get_parser_from_args(args)

    with parser:
        entity_id: str | None = None
        if args.entity:
            entity_id = parser.resolve_entity_id(args.entity)

        wars: list[dict] = []
        for ec in parser.event_collections:
            if ec.get("type") != "war":
                continue
            if args.active and not _is_ongoing(ec):
                continue
            if entity_id and not _collection_involves_entity(ec, entity_id):
                continue
            wars.append(ec)

        wars.sort(key=lambda w: _int_or_zero(w.get("start_year")))

        if args.json:
            print_json([_war_record(w, parser) for w in wars])
            return

        if not wars:
            print("No wars found.")
            return

        print(f"{'ID':>6}  {'War Name':<45}  {'Years':<20}  {'Aggressor':<25}  {'Defender':<25}  Battles")
        print("-" * 155)
        for w in wars:
            name = (w.get("name") or "Unnamed War").title()
            years = _format_year_range(w)
            aggressor = parser.get_entity_name(w.get("aggressor_ent_id", ""))
            defender = parser.get_entity_name(w.get("defender_ent_id", ""))
            sub_cols = _ensure_list(w.get("eventcol"))
            print(
                f"{w.get('id', '?'):>6}  {name:<45}  {years:<20}  "
                f"{aggressor:<25}  {defender:<25}  {len(sub_cols)}"
            )

        print(f"\nTotal: {len(wars)} war(s)")


def _war_record(w: dict, parser: LegendsParser) -> dict:
    """Serialisable summary of a war collection."""
    return {
        "id": w.get("id"),
        "name": (w.get("name") or "").title(),
        "start_year": w.get("start_year"),
        "end_year": w.get("end_year"),
        "aggressor": parser.get_entity_name(w.get("aggressor_ent_id", "")),
        "defender": parser.get_entity_name(w.get("defender_ent_id", "")),
        "sub_collections": len(_ensure_list(w.get("eventcol"))),
        "events": len(_ensure_list(w.get("event"))),
    }


# ---------------------------------------------------------------------------
# Battles subcommand
# ---------------------------------------------------------------------------

def cmd_battles(args: argparse.Namespace) -> None:
    """List battles from the Legends XML."""
    parser = get_parser_from_args(args)

    with parser:
        entity_id: str | None = None
        site_id: str | None = None
        if args.entity:
            entity_id = parser.resolve_entity_id(args.entity)
        if args.site:
            site_id = parser.resolve_site_id(args.site)

        # Year filter: --year sets both bounds; --year-from/--year-to override
        year_from = args.year_from if args.year_from is not None else args.year
        year_to = args.year_to if args.year_to is not None else args.year

        battles: list[dict] = []
        for ec in parser.event_collections:
            if ec.get("type") != "battle":
                continue
            if args.active and not _is_ongoing(ec):
                continue
            if entity_id and not _collection_involves_entity(ec, entity_id):
                continue
            if site_id and not _collection_involves_site(ec, site_id):
                continue
            # Year filter on start_year
            sy = _int_or_zero(ec.get("start_year"))
            if year_from is not None and sy < year_from:
                continue
            if year_to is not None and sy > year_to:
                continue
            battles.append(ec)

        battles.sort(key=lambda b: _int_or_zero(b.get("start_year")))

        if args.json:
            print_json([_battle_record(b, parser) for b in battles])
            return

        if not battles:
            print("No battles found.")
            return

        print(
            f"{'ID':>6}  {'Battle Name':<45}  {'Year':<6}  "
            f"{'Attacker':<25}  {'Defender':<25}  {'Site':<20}  "
            f"{'A.Dead':>6}  {'D.Dead':>6}"
        )
        print("-" * 155)
        for b in battles:
            name = (b.get("name") or "Unnamed Battle").title()
            year = format_year(b.get("start_year"))
            attacker = _resolve_battle_attacker(b, parser)
            defender = _resolve_battle_defender(b, parser)
            site_name = parser.get_site_name(b["site_id"]) if b.get("site_id") else "—"
            a_deaths = _count_squad_deaths(b, "attacking")
            d_deaths = _count_squad_deaths(b, "defending")
            print(
                f"{b.get('id', '?'):>6}  {name:<45}  {year:<6}  "
                f"{attacker:<25}  {defender:<25}  {site_name:<20}  "
                f"{a_deaths:>6}  {d_deaths:>6}"
            )

        print(f"\nTotal: {len(battles)} battle(s)")


def _resolve_battle_attacker(b: dict, parser: LegendsParser) -> str:
    """Best-effort attacker entity name for a battle collection."""
    eid = b.get("attacking_enid")
    if isinstance(eid, list):
        eid = eid[0] if eid else None
    if eid:
        return parser.get_entity_name(eid)
    # Fall back to aggressor_ent_id (present on some versions)
    eid = b.get("aggressor_ent_id")
    if eid:
        return parser.get_entity_name(eid)
    return "Unknown"


def _resolve_battle_defender(b: dict, parser: LegendsParser) -> str:
    """Best-effort defender entity name for a battle collection."""
    eid = b.get("defending_enid")
    if isinstance(eid, list):
        eid = eid[0] if eid else None
    if eid:
        return parser.get_entity_name(eid)
    eid = b.get("defender_ent_id")
    if eid:
        return parser.get_entity_name(eid)
    return "Unknown"


def _count_squad_deaths(b: dict, side: str) -> int:
    """Sum squad deaths for *side* ('attacking' or 'defending')."""
    val = b.get(f"{side}_squad_deaths")
    if val is None:
        return 0
    if isinstance(val, list):
        return sum(_int_or_zero(v) for v in val)
    return _int_or_zero(val)


def _battle_record(b: dict, parser: LegendsParser) -> dict:
    """Serialisable summary of a battle collection."""
    return {
        "id": b.get("id"),
        "name": (b.get("name") or "").title(),
        "start_year": b.get("start_year"),
        "attacker": _resolve_battle_attacker(b, parser),
        "defender": _resolve_battle_defender(b, parser),
        "site": parser.get_site_name(b["site_id"]) if b.get("site_id") else None,
        "coords": b.get("coords"),
        "attacking_squad_deaths": _count_squad_deaths(b, "attacking"),
        "defending_squad_deaths": _count_squad_deaths(b, "defending"),
        "events": len(_ensure_list(b.get("event"))),
    }


# ---------------------------------------------------------------------------
# Detail subcommand
# ---------------------------------------------------------------------------

def cmd_detail(args: argparse.Namespace) -> None:
    """Show detailed information for a single event collection."""
    parser = get_parser_from_args(args)

    with parser:
        ec_map = _build_ec_map(parser)

        # Resolve by ID first, then by name substring
        ec = ec_map.get(str(args.collection))
        if ec is None:
            needle = args.collection.lower()
            matches = [
                c for c in parser.event_collections
                if needle in (c.get("name") or "").lower()
            ]
            if len(matches) == 1:
                ec = matches[0]
            elif len(matches) > 1:
                print(f"Ambiguous name '{args.collection}' matched {len(matches)} collections:")
                for m in matches[:15]:
                    print(f"  [{m.get('id')}] {(m.get('name') or '').title()} ({m.get('type')})")
                sys.exit(1)
            else:
                print(f"No event collection found for '{args.collection}'.")
                sys.exit(1)

        if args.json:
            print_json(_detail_record(ec, parser, ec_map))
            return

        _print_detail(ec, parser, ec_map)


def _print_detail(ec: dict, parser: LegendsParser, ec_map: dict[str, dict]) -> None:
    """Pretty-print detailed information for an event collection."""
    ctype = ec.get("type", "unknown")
    name = (ec.get("name") or "Unnamed").title()

    # -- Header
    print(f"=== {name} ===")
    print(f"  Type: {ctype}")
    print(f"  ID:   {ec.get('id')}")
    print(f"  Years: {_format_year_range(ec)}")
    print()

    # -- Participants
    print("--- Participants ---")
    if ctype == "war":
        _print_field(ec, "aggressor_ent_id", "Aggressor", parser.get_entity_name)
        _print_field(ec, "defender_ent_id", "Defender", parser.get_entity_name)
    elif ctype == "battle":
        _print_list_field(ec, "attacking_enid", "Attacking entities", parser.get_entity_name)
        _print_list_field(ec, "defending_enid", "Defending entities", parser.get_entity_name)
        _print_list_field(ec, "attacking_merc_enid", "Attacking mercs", parser.get_entity_name)
        _print_list_field(ec, "defending_merc_enid", "Defending mercs", parser.get_entity_name)
        _print_list_field(ec, "attacking_hfid", "Attacking notables", parser.get_hf_name)
        _print_list_field(ec, "defending_hfid", "Defending notables", parser.get_hf_name)
        _print_list_field(ec, "individual_merc", "Individual mercs", parser.get_hf_name)
        if ec.get("site_id"):
            print(f"  Site: {parser.get_site_name(ec['site_id'])}")
        if ec.get("coords"):
            print(f"  Coordinates: {ec['coords']}")
        a_deaths = _count_squad_deaths(ec, "attacking")
        d_deaths = _count_squad_deaths(ec, "defending")
        print(f"  Attacking squad deaths: {a_deaths}")
        print(f"  Defending squad deaths: {d_deaths}")
    else:
        # Generic: dump any *_ent_id / *_enid / *_hfid fields
        for key, val in sorted(ec.items()):
            if key.endswith(("_ent_id", "_enid")) and val:
                for v in _ensure_list(val):
                    print(f"  {key}: {parser.get_entity_name(v)}")
            elif key.endswith("_hfid") and val:
                for v in _ensure_list(val):
                    print(f"  {key}: {parser.get_hf_name(v)}")
    print()

    # -- Sub-collections
    sub_col_ids = _ensure_list(ec.get("eventcol"))
    if sub_col_ids:
        print(f"--- Sub-collections ({len(sub_col_ids)}) ---")
        for sc_id in sub_col_ids:
            sub = ec_map.get(str(sc_id))
            if sub:
                sname = (sub.get("name") or "Unnamed").title()
                syear = format_year(sub.get("start_year"))
                stype = sub.get("type", "?")
                print(f"  [{sc_id}] {sname} ({stype}, year {syear})")
            else:
                print(f"  [{sc_id}] (not found)")
        print()

    # -- Events
    event_ids = _ensure_list(ec.get("event"))
    if event_ids:
        ev_map = _build_event_map(parser)
        matched_events = [ev_map[eid] for eid in event_ids if eid in ev_map]
        matched_events.sort(key=lambda e: (_int_or_zero(e.get("year")), _int_or_zero(e.get("seconds72"))))

        print(f"--- Events ({len(matched_events)}/{len(event_ids)}) ---")
        deaths: list[dict] = []
        for ev in matched_events:
            etype = ev.get("type", "unknown")
            year = format_year(ev.get("year"))
            line = f"  [{ev.get('id')}] Year {year} — {etype}"

            # Add useful context for common event types
            extras = _event_extras(ev, parser)
            if extras:
                line += f"  ({extras})"
            print(line)

            if etype == "hf died":
                deaths.append(ev)
        print()

        # -- Casualties
        if deaths:
            print(f"--- Casualties ({len(deaths)}) ---")
            for d in deaths:
                hf_id = d.get("hfid")
                hf_name = parser.get_hf_name(hf_id) if hf_id else "Unknown"
                cause = d.get("death_cause") or d.get("cause") or "unknown cause"
                slayer_id = d.get("slayer_hfid")
                slayer = f" by {parser.get_hf_name(slayer_id)}" if slayer_id else ""
                year = format_year(d.get("year"))
                print(f"  Year {year}: {hf_name} — {cause}{slayer}")
            print()
    else:
        print("--- Events: none ---\n")


def _print_field(ec: dict, key: str, label: str, resolver) -> None:
    """Print a single resolved field if present."""
    val = ec.get(key)
    if val:
        print(f"  {label}: {resolver(val)}")


def _print_list_field(ec: dict, key: str, label: str, resolver) -> None:
    """Print a multi-valued field, resolving each ID."""
    vals = _ensure_list(ec.get(key))
    if vals:
        names = [resolver(v) for v in vals]
        print(f"  {label}: {', '.join(names)}")


def _event_extras(ev: dict, parser: LegendsParser) -> str:
    """Return a brief description string for common event types."""
    etype = ev.get("type", "")
    parts: list[str] = []

    if etype == "hf died":
        hf_id = ev.get("hfid")
        if hf_id:
            parts.append(parser.get_hf_name(hf_id))
        cause = ev.get("death_cause") or ev.get("cause")
        if cause:
            parts.append(cause)
        slayer = ev.get("slayer_hfid")
        if slayer:
            parts.append(f"slayer: {parser.get_hf_name(slayer)}")
    elif etype in ("hf wounded", "hf simple battle event"):
        for role, field in [("attacker", "attacker_hfid"), ("defender", "defender_hfid")]:
            hid = ev.get(field) or ev.get(f"group_{field.split('_')[0]}_hfid")
            if hid:
                parts.append(f"{role}: {parser.get_hf_name(hid)}")
    elif etype == "site conquered":
        site = ev.get("site_id")
        if site:
            parts.append(parser.get_site_name(site))
    elif etype == "hf attacked site":
        site = ev.get("site_id")
        if site:
            parts.append(f"site: {parser.get_site_name(site)}")
        hf = ev.get("attacker_hfid")
        if hf:
            parts.append(f"attacker: {parser.get_hf_name(hf)}")
    elif etype in ("add hf entity link", "remove hf entity link"):
        hf = ev.get("hfid")
        if hf:
            parts.append(parser.get_hf_name(hf))
        eid = ev.get("civ_id")
        if eid:
            parts.append(parser.get_entity_name(eid))

    return "; ".join(parts)


def _detail_record(ec: dict, parser: LegendsParser, ec_map: dict[str, dict]) -> dict:
    """Serialisable detail record for JSON output."""
    ev_map = _build_event_map(parser)

    # Resolve sub-collections
    sub_col_ids = _ensure_list(ec.get("eventcol"))
    sub_cols = []
    for sc_id in sub_col_ids:
        sub = ec_map.get(str(sc_id))
        if sub:
            sub_cols.append({
                "id": sc_id,
                "name": (sub.get("name") or "").title(),
                "type": sub.get("type"),
                "start_year": sub.get("start_year"),
                "end_year": sub.get("end_year"),
            })

    # Resolve events
    event_ids = _ensure_list(ec.get("event"))
    resolved_events = []
    deaths = []
    for eid in event_ids:
        ev = ev_map.get(str(eid))
        if not ev:
            continue
        resolved_events.append(ev)
        if ev.get("type") == "hf died":
            deaths.append({
                "event_id": ev.get("id"),
                "year": ev.get("year"),
                "hf_id": ev.get("hfid"),
                "hf_name": parser.get_hf_name(ev["hfid"]) if ev.get("hfid") else None,
                "cause": ev.get("death_cause") or ev.get("cause"),
                "slayer_hfid": ev.get("slayer_hfid"),
                "slayer_name": parser.get_hf_name(ev["slayer_hfid"]) if ev.get("slayer_hfid") else None,
            })

    # Build participants dict based on type
    participants: dict[str, Any] = {}
    ctype = ec.get("type", "")
    if ctype == "war":
        participants["aggressor"] = parser.get_entity_name(ec.get("aggressor_ent_id", ""))
        participants["defender"] = parser.get_entity_name(ec.get("defender_ent_id", ""))
    elif ctype == "battle":
        participants["attacking_entities"] = [parser.get_entity_name(v) for v in _ensure_list(ec.get("attacking_enid"))]
        participants["defending_entities"] = [parser.get_entity_name(v) for v in _ensure_list(ec.get("defending_enid"))]
        participants["attacking_squad_deaths"] = _count_squad_deaths(ec, "attacking")
        participants["defending_squad_deaths"] = _count_squad_deaths(ec, "defending")
        if ec.get("site_id"):
            participants["site"] = parser.get_site_name(ec["site_id"])

    return {
        "id": ec.get("id"),
        "name": (ec.get("name") or "").title(),
        "type": ctype,
        "start_year": ec.get("start_year"),
        "end_year": ec.get("end_year"),
        "participants": participants,
        "sub_collections": sub_cols,
        "events": resolved_events,
        "casualties": deaths,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subcommands."""
    top = argparse.ArgumentParser(
        description="Battle and war analysis from Dwarf Fortress Legends XML.",
    )
    add_common_args(top)
    top.add_argument(
        "--entity",
        type=str,
        default=None,
        help="Filter by participating entity (name or ID).",
    )
    top.add_argument(
        "--site",
        type=str,
        default=None,
        help="Filter by site (name or ID).",
    )
    top.add_argument(
        "--active",
        action="store_true",
        default=False,
        help="Only show ongoing wars/battles (end_year == -1).",
    )

    subs = top.add_subparsers(dest="command")

    # wars
    wars_p = subs.add_parser("wars", help="List all wars.")
    add_common_args(wars_p)
    wars_p.add_argument("--entity", type=str, default=None, help="Filter by entity.")
    wars_p.add_argument("--active", action="store_true", default=False, help="Only ongoing.")

    # battles
    bat_p = subs.add_parser("battles", help="List all battles.")
    add_common_args(bat_p)
    bat_p.add_argument("--entity", type=str, default=None, help="Filter by entity.")
    bat_p.add_argument("--site", type=str, default=None, help="Filter by site.")
    bat_p.add_argument("--active", action="store_true", default=False, help="Only ongoing.")

    # detail
    det_p = subs.add_parser("detail", help="Show details for an event collection.")
    add_common_args(det_p)
    det_p.add_argument(
        "collection",
        type=str,
        help="Event collection ID or name substring.",
    )

    return top


def main() -> None:
    """Entry point."""
    configure_output()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "wars":
        cmd_wars(args)
    elif args.command == "battles":
        cmd_battles(args)
    elif args.command == "detail":
        cmd_detail(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
