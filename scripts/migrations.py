"""
migrations.py — Migration wave tracker from DF Legends XML.

Lists all figures who settled at a site in a given year range, grouped by
arrival wave (same seconds72 = same wave).  Each settler includes a detailed
profile: name, race, caste, age, profession, top skills, family, and entity
memberships.

Usage:
    python scripts/migrations.py testfort --year 100
    python scripts/migrations.py testfort --year-from 99 --year-to 102
    python scripts/migrations.py 200 --year 99 --json
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
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
    skill_level_name,
)


# ---------------------------------------------------------------------------
# Season mapping (seconds72 → human-readable season name)
# ---------------------------------------------------------------------------

# A DF year has 403200 seconds72.  Seasons span roughly equal quarters.
_SEASON_THRESHOLDS = [
    (302400, "Late Winter"),
    (201600, "Late Autumn"),
    (100800, "Late Summer"),
    (0, "Early Spring"),
]


def _season_name(seconds72: int) -> str:
    """Return an approximate DF season name for a seconds72 value."""
    for threshold, name in _SEASON_THRESHOLDS:
        if seconds72 >= threshold:
            return name
    return "Early Spring"


# ---------------------------------------------------------------------------
# Profile building
# ---------------------------------------------------------------------------


def _build_settler_profile(
    hf_id: str,
    parser: LegendsParser,
    event_year: int,
) -> dict[str, Any]:
    """Assemble a profile dict for a single settling historical figure."""
    hf = parser.hf_map.get(hf_id, {})

    name = (hf.get("name") or "Unnamed").title()
    race = (hf.get("race") or "unknown").upper()
    caste = (hf.get("caste") or "").lower()
    profession = (hf.get("associated_type") or "STANDARD").replace("_", " ").title()

    # Age at settlement
    birth_year = hf.get("birth_year")
    age: int | None = None
    if birth_year is not None:
        try:
            by = int(birth_year)
            if by >= 0:
                age = event_year - by
        except (ValueError, TypeError):
            pass

    # Top 3 skills by IP
    raw_skills = hf.get("hf_skills", [])
    sorted_skills = sorted(
        raw_skills,
        key=lambda s: int(s.get("total_ip", 0)),
        reverse=True,
    )
    top_skills: list[dict[str, Any]] = []
    for sk in sorted_skills[:3]:
        ip = int(sk.get("total_ip", 0))
        if ip <= 0:
            continue
        skill_name = (sk.get("skill") or "").replace("_", " ").title()
        top_skills.append({
            "skill": skill_name,
            "total_ip": ip,
            "level": skill_level_name(ip),
        })

    # Family links
    family: list[dict[str, str]] = []
    for link in hf.get("hf_links", []):
        link_type = link.get("link_type", "")
        if link_type in ("spouse", "child", "father", "mother"):
            other_id = str(link.get("hfid", ""))
            other_name = parser.get_hf_name(other_id)
            family.append({"relation": link_type, "name": other_name, "hf_id": other_id})

    # Entity memberships (non-enemy)
    entities: list[dict[str, str]] = []
    for link in hf.get("entity_links", []):
        link_type = link.get("link_type", "")
        if link_type in ("enemy",):
            continue
        ent_id = str(link.get("entity_id", ""))
        ent_name = parser.get_entity_name(ent_id)
        entities.append({
            "entity_id": ent_id,
            "entity_name": ent_name,
            "link_type": link_type,
        })

    return {
        "hf_id": hf_id,
        "name": name,
        "race": race,
        "caste": caste,
        "age": age,
        "profession": profession,
        "skills": top_skills,
        "family": family,
        "entities": entities,
    }


def build_migration_data(
    site_id: str,
    parser: LegendsParser,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict[str, Any]:
    """Find all settlement events at *site_id* and group into waves.

    Returns a dict suitable for JSON output or human-readable formatting.
    """
    site = parser.site_map.get(site_id, {})
    site_name = (site.get("name") or "Unknown").title()

    # Gather all "change hf state" events with state=settled at this site
    events = parser.filter_events(
        year_from=year_from,
        year_to=year_to,
        event_type="change hf state",
        site_id=site_id,
    )
    settled_events = [ev for ev in events if ev.get("state") == "settled"]

    # Group by (year, seconds72) for wave detection
    wave_key = lambda ev: (int(ev.get("year", 0)), int(ev.get("seconds72", 0)))
    grouped: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for ev in settled_events:
        grouped[wave_key(ev)].append(ev)

    # Build wave list in chronological order
    waves: list[dict[str, Any]] = []
    wave_num = 0
    for key in sorted(grouped.keys()):
        wave_num += 1
        year, sec72 = key
        settlers: list[dict[str, Any]] = []
        for ev in grouped[key]:
            hf_id = str(ev.get("hfid", ""))
            if hf_id and hf_id != "-1":
                settlers.append(_build_settler_profile(hf_id, parser, year))
        waves.append({
            "wave": wave_num,
            "year": year,
            "seconds72": sec72,
            "season": _season_name(sec72),
            "settlers": settlers,
        })

    total_settlers = sum(len(w["settlers"]) for w in waves)

    return {
        "site_id": site_id,
        "site_name": site_name,
        "year_from": year_from,
        "year_to": year_to,
        "total_settlers": total_settlers,
        "total_waves": len(waves),
        "waves": waves,
    }


# ---------------------------------------------------------------------------
# Human-readable output
# ---------------------------------------------------------------------------


def _format_skills(skills: list[dict[str, Any]]) -> str:
    """Return a comma-separated skill summary string."""
    return ", ".join(f"{s['level']} {s['skill']}" for s in skills)


def _format_family(family: list[dict[str, str]]) -> str:
    """Return a comma-separated family string."""
    return ", ".join(f"{f['relation']} {f['name']}" for f in family)


def _format_entities(entities: list[dict[str, str]]) -> str:
    """Return a comma-separated entity membership string."""
    return ", ".join(e["entity_name"] for e in entities)


def print_migration_data(data: dict[str, Any]) -> None:
    """Print migration data in human-readable format."""
    waves = data["waves"]

    if not waves:
        print(f"No migrations found at {data['site_name']}.")
        return

    for w in waves:
        print(f"\n=== Year {w['year']}, {w['season']} (Wave {w['wave']}) ===\n")
        for s in w["settlers"]:
            age_str = f", age {s['age']}" if s["age"] is not None else ""
            print(f"  {s['name']} ({s['race']}, {s['caste']}{age_str})")
            print(f"    Profession: {s['profession']}")
            if s["skills"]:
                print(f"    Skills: {_format_skills(s['skills'])}")
            if s["family"]:
                print(f"    Family: {_format_family(s['family'])}")
            if s["entities"]:
                print(f"    Entity: {_format_entities(s['entities'])}")
            print()

    wave_word = "wave" if data["total_waves"] == 1 else "waves"
    settler_word = "settler" if data["total_settlers"] == 1 else "settlers"
    print(f"--- {data['total_settlers']} {settler_word} in {data['total_waves']} {wave_word} ---")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and display migration data."""
    configure_output()
    ap = argparse.ArgumentParser(
        description="List migration waves at a site from Dwarf Fortress Legends XML.",
    )
    ap.add_argument(
        "name",
        type=str,
        help="Site name (partial, case-insensitive) or numeric site ID.",
    )
    add_common_args(ap)
    args = ap.parse_args()

    # Require at least one year filter
    if args.year is None and args.year_from is None and args.year_to is None:
        ap.error("At least one of --year, --year-from, or --year-to is required.")

    # Resolve year range
    year_from: int | None = args.year_from
    year_to: int | None = args.year_to
    if args.year is not None:
        year_from = args.year
        year_to = args.year

    with get_parser_from_args(args) as parser:
        # Resolve the site
        if args.name.isdigit():
            site = parser.site_map.get(args.name)
            if site is None:
                print(f"No site with ID {args.name}.", file=sys.stderr)
                sys.exit(1)
            site_id = args.name
        else:
            matches = parser.find_site_by_name(args.name)
            if not matches:
                print(f"No sites matching '{args.name}'.", file=sys.stderr)
                sys.exit(1)
            if len(matches) > 1:
                print(
                    f"'{args.name}' matches {len(matches)} sites. "
                    "Be more specific or use a numeric ID.\n",
                    file=sys.stderr,
                )
                for m in matches:
                    sid = m.get("id", "?")
                    sname = (m.get("name") or "Unnamed").title()
                    print(f"  [{sid}] {sname}", file=sys.stderr)
                sys.exit(1)
            site_id = str(matches[0]["id"])

        data = build_migration_data(site_id, parser, year_from, year_to)

        if args.json:
            print_json(data)
        else:
            print_migration_data(data)


if __name__ == "__main__":
    main()
