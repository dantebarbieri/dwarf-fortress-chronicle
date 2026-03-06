"""
interactions.py — Entity-to-entity interaction log from Dwarf Fortress Legends XML.

Shows all interactions between two entities over time: wars, battles, trade,
diplomacy, site captures, and other shared events.  Helps Atir understand
civ-level relationships.

Usage:
    python scripts/interactions.py "the guilds of testing" "the dark horde"
    python scripts/interactions.py 100 102 --year-from 100 --json
    python scripts/interactions.py "guilds of testing" "dark horde" --category wars
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
    event_involves_entity,
    format_year,
    get_parser_from_args,
    print_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_CATEGORIES = ("wars", "battles", "trade", "diplomacy", "site_captures", "other", "all")

# Event types mapped to interaction categories.
_TRADE_TYPES = frozenset({"merchant"})
_DIPLOMACY_TYPES = frozenset({
    "diplomat lost",
    "agreement made",
    "agreement concluded",
    "agreement rejected",
    "peace accepted",
    "peace rejected",
    "first contact",
})
_SITE_CAPTURE_TYPES = frozenset({
    "site conquered",
    "hf attacked site",
    "site taken over",
    "site destroyed",
    "site tribute forced",
    "insurrection started",
    "reclaim site",
})


def _ensure_list(val: Any) -> list[str]:
    """Normalise a value that may be a string, list, or None into a list."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def _int_or_zero(val: Any) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _collection_involves_both(ec: dict, eid1: str, eid2: str) -> bool:
    """Return True if *ec* has both entities as opposing participants."""
    id1, id2 = str(eid1), str(eid2)
    fields_a = ("aggressor_ent_id", "attacking_enid")
    fields_d = ("defender_ent_id", "defending_enid")

    all_fields = fields_a + fields_d + ("attacking_merc_enid", "defending_merc_enid", "entity_id", "civ_id")

    found: set[str] = set()
    for field in all_fields:
        val = ec.get(field)
        if val is None:
            continue
        for v in (_ensure_list(val) if isinstance(val, list) else [val]):
            sv = str(v)
            if sv == id1:
                found.add(id1)
            elif sv == id2:
                found.add(id2)
    return id1 in found and id2 in found


def _format_year_range(ec: dict) -> str:
    start = format_year(ec.get("start_year"))
    end_raw = ec.get("end_year")
    end = "ongoing" if str(end_raw).strip() in ("-1", "") else format_year(end_raw)
    if start == end:
        return start
    return f"{start}\u2013{end}"


def _count_squad_deaths(ec: dict, side: str) -> int:
    val = ec.get(f"{side}_squad_deaths")
    if val is None:
        return 0
    if isinstance(val, list):
        return sum(_int_or_zero(v) for v in val)
    return _int_or_zero(val)


def _count_squad_number(ec: dict, side: str) -> int:
    val = ec.get(f"{side}_squad_number")
    if val is None:
        return 0
    if isinstance(val, list):
        return sum(_int_or_zero(v) for v in val)
    return _int_or_zero(val)


def _squad_race(ec: dict, side: str) -> str:
    val = ec.get(f"{side}_squad_race")
    if val is None:
        return "unknown"
    if isinstance(val, list):
        return ", ".join(str(v).lower() for v in val)
    return str(val).lower()


def _categorise_event(event: dict) -> str:
    etype = (event.get("type") or "").lower()
    if etype in _TRADE_TYPES:
        return "trade"
    if etype in _DIPLOMACY_TYPES:
        return "diplomacy"
    if etype in _SITE_CAPTURE_TYPES:
        return "site_captures"
    return "other"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def find_interactions(
    lp: LegendsParser,
    eid1: str,
    eid2: str,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    category: str = "all",
) -> dict[str, list[dict]]:
    """Find all interactions between two entities.

    Returns a dict keyed by category: wars, battles, trade, diplomacy,
    site_captures, other.  Each value is a list of interaction records
    sorted chronologically.
    """
    results: dict[str, list[dict]] = {
        "wars": [],
        "battles": [],
        "trade": [],
        "diplomacy": [],
        "site_captures": [],
        "other": [],
    }

    want_collections = category in ("all", "wars", "battles")
    want_events = category in ("all", "trade", "diplomacy", "site_captures", "other")

    # --- Event collections (wars, battles) ---
    if want_collections:
        ec_map: dict[str, dict] = {str(ec["id"]): ec for ec in lp.event_collections if "id" in ec}

        for ec in lp.event_collections:
            ec_type = (ec.get("type") or "").lower()
            if ec_type not in ("war", "battle"):
                continue
            if not _collection_involves_both(ec, eid1, eid2):
                continue

            sy = _int_or_zero(ec.get("start_year"))
            if year_from is not None and sy < year_from:
                continue
            if year_to is not None and sy > year_to:
                continue

            cat = "wars" if ec_type == "war" else "battles"
            if category not in ("all", cat):
                continue

            record: dict[str, Any] = {
                "type": ec_type,
                "id": ec.get("id"),
                "name": (ec.get("name") or "Unnamed").title(),
                "start_year": ec.get("start_year"),
                "end_year": ec.get("end_year"),
                "_sort_key": (sy, _int_or_zero(ec.get("start_seconds72"))),
            }

            if ec_type == "war":
                record["aggressor"] = lp.get_entity_name(ec.get("aggressor_ent_id", ""))
                record["defender"] = lp.get_entity_name(ec.get("defender_ent_id", ""))
                sub_ids = _ensure_list(ec.get("eventcol"))
                record["battle_count"] = len(sub_ids)
            elif ec_type == "battle":
                record["attacker"] = lp.get_entity_name(
                    ec.get("attacking_enid") or ec.get("aggressor_ent_id") or ""
                )
                record["defender"] = lp.get_entity_name(
                    ec.get("defending_enid") or ec.get("defender_ent_id") or ""
                )
                record["attacker_number"] = _count_squad_number(ec, "attacking")
                record["attacker_race"] = _squad_race(ec, "attacking")
                record["attacker_deaths"] = _count_squad_deaths(ec, "attacking")
                record["defender_number"] = _count_squad_number(ec, "defending")
                record["defender_race"] = _squad_race(ec, "defending")
                record["defender_deaths"] = _count_squad_deaths(ec, "defending")
                # Resolve location
                if ec.get("site_id"):
                    record["location"] = lp.get_site_name(ec["site_id"])
                elif ec.get("coords"):
                    record["location"] = ec["coords"]
                else:
                    record["location"] = None

            results[cat].append(record)

    # --- Individual events ---
    if want_events:
        for event in lp.events:
            if not event_involves_entity(event, eid1):
                continue
            if not event_involves_entity(event, eid2):
                continue

            ey = _int_or_zero(event.get("year"))
            if year_from is not None and ey < year_from:
                continue
            if year_to is not None and ey > year_to:
                continue

            cat = _categorise_event(event)
            if category not in ("all", cat):
                continue

            record = {
                "type": event.get("type", "unknown"),
                "id": event.get("id"),
                "year": event.get("year"),
                "seconds72": event.get("seconds72"),
                "_sort_key": (ey, _int_or_zero(event.get("seconds72"))),
            }

            # Add category-specific detail
            etype = (event.get("type") or "").lower()
            if etype == "merchant":
                record["trader_entity"] = lp.get_entity_name(
                    event.get("trader_entity_id") or ""
                )
                if event.get("site_id"):
                    record["site"] = lp.get_site_name(event["site_id"])
            elif etype in _SITE_CAPTURE_TYPES:
                if event.get("site_id"):
                    record["site"] = lp.get_site_name(event["site_id"])

            results[cat].append(record)

    # Sort each category chronologically
    for cat_list in results.values():
        cat_list.sort(key=lambda r: r.get("_sort_key", (0, 0)))

    return results


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------

def _print_war(rec: dict) -> None:
    yr = _format_year_range(rec)
    print(f"  {rec['name']} (Year {yr})")
    print(f"    Aggressor: {rec.get('aggressor', 'Unknown')}")
    print(f"    Defender: {rec.get('defender', 'Unknown')}")
    print(f"    Battles: {rec.get('battle_count', 0)}")


def _print_battle(rec: dict) -> None:
    yr = format_year(rec.get("start_year"))
    print(f"  {rec['name']} (Year {yr})")
    a_num = rec.get("attacker_number", "?")
    a_race = rec.get("attacker_race", "?")
    a_dead = rec.get("attacker_deaths", 0)
    print(f"    Attacker: {rec.get('attacker', 'Unknown')} ({a_num} {a_race}, {a_dead} killed)")
    d_num = rec.get("defender_number", "?")
    d_race = rec.get("defender_race", "?")
    d_dead = rec.get("defender_deaths", 0)
    print(f"    Defender: {rec.get('defender', 'Unknown')} ({d_num} {d_race}, {d_dead} killed)")
    loc = rec.get("location")
    if loc:
        print(f"    Location: {loc}")


def _print_event(rec: dict) -> None:
    yr = format_year(rec.get("year"))
    etype = rec.get("type", "unknown")
    parts = [f"  Year {yr}: {etype}"]
    if rec.get("trader_entity"):
        parts.append(f"trader: {rec['trader_entity']}")
    if rec.get("site"):
        parts.append(f"at {rec['site']}")
    print("  ".join(parts))


_CATEGORY_LABELS = {
    "wars": "Wars",
    "battles": "Battles",
    "trade": "Trade",
    "diplomacy": "Diplomacy",
    "site_captures": "Site Captures",
    "other": "Other",
}


def print_text(
    entity1_name: str,
    entity2_name: str,
    interactions: dict[str, list[dict]],
) -> None:
    """Print human-readable interaction log."""
    header = f"Interactions: {entity1_name} \u2194 {entity2_name}"
    print(header)
    print("=" * len(header))
    print()

    total = 0
    for cat, records in interactions.items():
        if not records:
            continue
        total += len(records)
        label = _CATEGORY_LABELS.get(cat, cat.title())
        print(f"=== {label} ===")
        for rec in records:
            rtype = rec.get("type", "")
            if rtype == "war":
                _print_war(rec)
            elif rtype == "battle":
                _print_battle(rec)
            else:
                _print_event(rec)
        print()

    print(f"--- {total} interaction(s) found ---")


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def build_json(
    eid1: str,
    entity1_name: str,
    eid2: str,
    entity2_name: str,
    interactions: dict[str, list[dict]],
) -> dict:
    """Build a serialisable dict for JSON output."""
    # Strip internal sort keys
    cleaned: dict[str, list[dict]] = {}
    total = 0
    for cat, records in interactions.items():
        clean = []
        for rec in records:
            r = {k: v for k, v in rec.items() if not k.startswith("_")}
            clean.append(r)
        cleaned[cat] = clean
        total += len(clean)

    summary = {cat: len(recs) for cat, recs in cleaned.items()}
    summary["total"] = total

    return {
        "entity_1": {"id": eid1, "name": entity1_name},
        "entity_2": {"id": eid2, "name": entity2_name},
        "interactions": cleaned,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Entity-to-entity interaction log from Dwarf Fortress Legends XML.",
    )
    parser.add_argument(
        "entity1",
        type=str,
        help="First entity name or ID.",
    )
    parser.add_argument(
        "entity2",
        type=str,
        help="Second entity name or ID.",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="all",
        choices=_VALID_CATEGORIES,
        help="Filter to a specific interaction category.",
    )
    add_common_args(parser)
    return parser


def main() -> None:
    """Entry point."""
    configure_output()
    ap = build_arg_parser()
    args = ap.parse_args()

    lp = get_parser_from_args(args)

    with lp:
        # Resolve entities
        try:
            eid1 = lp.resolve_entity_id(args.entity1)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        try:
            eid2 = lp.resolve_entity_id(args.entity2)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        if eid1 == eid2:
            print("Error: Both arguments resolve to the same entity.", file=sys.stderr)
            sys.exit(1)

        name1 = lp.get_entity_name(eid1).lower()
        name2 = lp.get_entity_name(eid2).lower()

        # Year filter: --year sets both bounds
        year_from = args.year_from if args.year_from is not None else args.year
        year_to = args.year_to if args.year_to is not None else args.year

        interactions = find_interactions(
            lp, eid1, eid2,
            year_from=year_from,
            year_to=year_to,
            category=args.category,
        )

        if args.json:
            print_json(build_json(eid1, name1, eid2, name2, interactions))
        else:
            print_text(name1, name2, interactions)


if __name__ == "__main__":
    main()
