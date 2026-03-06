"""
figure.py — Comprehensive historical-figure profile from DF Legends XML.

Works for any historical figure (dwarves, goblins, megabeasts, etc.). Displays
identity, status, entity memberships, positions held, skills, family, artifacts,
goals, and a brief event summary.

Usage:
    python scripts/figure.py "atir"
    python scripts/figure.py 12345 --json
    python scripts/figure.py "urist" --race DWARF
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Ensure the DF root is on sys.path so `scripts.legends_parser` resolves.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.legends_parser import (
    LegendsParser,
    add_common_args,
    configure_output,
    format_hf_summary,
    format_year,
    get_parser_from_args,
    print_json,
    skill_level_name,
)


# ---------------------------------------------------------------------------
# Profile building
# ---------------------------------------------------------------------------


def _normalize_list(value: Any) -> list[str]:
    """Ensure a value is a list of strings (handles scalar or list)."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _build_identity(hf: dict[str, Any]) -> dict[str, Any]:
    """Extract the identity block from a historical-figure dict."""
    return {
        "name": (hf.get("name") or "Unnamed").title(),
        "race": (hf.get("race") or "unknown").replace("_", " ").title(),
        "caste": (hf.get("caste") or "").replace("_", " ").title(),
        "birth_year": format_year(hf.get("birth_year")),
        "death_year": format_year(hf.get("death_year")),
        "associated_type": hf.get("associated_type") or "",
    }


def _build_status(hf: dict[str, Any]) -> dict[str, Any]:
    """Extract deity/force flags, spheres, and active interactions."""
    interactions = _normalize_list(hf.get("active_interaction"))
    spheres = _normalize_list(hf.get("spheres"))
    return {
        "deity": bool(hf.get("deity")),
        "force": bool(hf.get("force")),
        "spheres": spheres,
        "active_interactions": interactions,
    }


def _build_entity_memberships(
    hf: dict[str, Any], parser: LegendsParser
) -> dict[str, list[dict[str, str]]]:
    """Categorise entity links into current and former memberships."""
    current: list[dict[str, str]] = []
    former: list[dict[str, str]] = []
    for link in hf.get("entity_links", []):
        entry = {
            "link_type": link.get("link_type", "unknown"),
            "entity_id": link.get("entity_id", ""),
            "entity_name": parser.get_entity_name(link.get("entity_id", "")),
        }
        if "former" in entry["link_type"].lower():
            former.append(entry)
        else:
            current.append(entry)
    return {"current": current, "former": former}


def _build_positions(
    hf: dict[str, Any], parser: LegendsParser
) -> dict[str, list[dict[str, str]]]:
    """Extract current and former position links."""
    current: list[dict[str, str]] = []
    for pos in hf.get("entity_position_links", []):
        current.append({
            "position_id": pos.get("position_profile_id", ""),
            "entity_id": pos.get("entity_id", ""),
            "entity_name": parser.get_entity_name(pos.get("entity_id", "")),
            "start_year": format_year(pos.get("start_year")),
        })
    former: list[dict[str, str]] = []
    for pos in hf.get("entity_former_position_links", []):
        former.append({
            "position_id": pos.get("position_profile_id", ""),
            "entity_id": pos.get("entity_id", ""),
            "entity_name": parser.get_entity_name(pos.get("entity_id", "")),
            "start_year": format_year(pos.get("start_year")),
            "end_year": format_year(pos.get("end_year")),
        })
    return {"current": current, "former": former}


def _build_skills(hf: dict[str, Any]) -> list[dict[str, Any]]:
    """Return top-10 skills sorted by IP descending."""
    skills: list[dict[str, Any]] = []
    for sk in hf.get("hf_skills", []):
        try:
            ip = int(sk.get("total_ip", 0))
        except (ValueError, TypeError):
            ip = 0
        skills.append({
            "skill": (sk.get("skill") or "unknown").replace("_", " ").upper(),
            "total_ip": ip,
            "level": skill_level_name(ip),
        })
    skills.sort(key=lambda s: s["total_ip"], reverse=True)
    return skills[:10]


def _build_family(
    hf: dict[str, Any], parser: LegendsParser
) -> list[dict[str, str]]:
    """Resolve hf_links into family relationships."""
    family: list[dict[str, str]] = []
    for link in hf.get("hf_links", []):
        link_type = link.get("link_type", "unknown")
        target_id = link.get("hfid", "")
        target_hf = parser.hf_map.get(str(target_id), {})
        name = (target_hf.get("name") or "Unknown").title()
        race = (target_hf.get("race") or "unknown").replace("_", " ").title()
        death_year = target_hf.get("death_year")
        alive = "alive" if format_year(death_year) == "present" else "dead"
        family.append({
            "relationship": link_type.replace("_", " ").title(),
            "name": name,
            "race": race,
            "status": alive,
            "hfid": str(target_id),
        })
    return family


def _build_artifacts(
    hf: dict[str, Any], parser: LegendsParser
) -> list[dict[str, str]]:
    """Find artifacts held by this figure."""
    held_ids = set(_normalize_list(hf.get("holds_artifact")))
    hf_id = str(hf.get("id", ""))
    # Also check artifact_map for holder_hfid
    for aid, art in parser.artifact_map.items():
        if str(art.get("holder_hfid", "")) == hf_id:
            held_ids.add(aid)
    artifacts: list[dict[str, str]] = []
    for aid in sorted(held_ids):
        art = parser.artifact_map.get(str(aid), {})
        artifacts.append({
            "id": str(aid),
            "name": (art.get("name") or art.get("name_string") or "Unknown").title(),
        })
    return artifacts


def _build_event_summary(
    hf_id: str,
    parser: LegendsParser,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """Count events by type for this figure; return top 10."""
    events = parser.get_hf_events(str(hf_id), year_from=year_from, year_to=year_to)
    counts: Counter[str] = Counter()
    for ev in events:
        counts[ev.get("type", "unknown")] += 1
    return [
        {"event_type": etype, "count": cnt}
        for etype, cnt in counts.most_common(10)
    ]


def build_profile(
    hf: dict[str, Any],
    parser: LegendsParser,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict[str, Any]:
    """Assemble the full profile dict for a historical figure."""
    hf_id = str(hf.get("id", ""))
    goals = _normalize_list(hf.get("goals"))
    return {
        "hf_id": hf_id,
        "identity": _build_identity(hf),
        "status": _build_status(hf),
        "entity_memberships": _build_entity_memberships(hf, parser),
        "positions": _build_positions(hf, parser),
        "top_skills": _build_skills(hf),
        "family": _build_family(hf, parser),
        "artifacts": _build_artifacts(hf, parser),
        "goals": goals,
        "event_summary": _build_event_summary(hf_id, parser, year_from, year_to),
    }


# ---------------------------------------------------------------------------
# Human-readable output
# ---------------------------------------------------------------------------


def _section(title: str) -> str:
    return f"\n{'=' * 60}\n  {title}\n{'=' * 60}"


def print_profile(profile: dict[str, Any]) -> None:
    """Print a profile dict in human-readable format."""
    ident = profile["identity"]
    status = profile["status"]

    # -- Identity --
    print(_section("Identity"))
    death_str = ident["death_year"] if ident["death_year"] != "present" else "alive"
    race_caste = f'{ident["race"]}, {ident["caste"]}' if ident["caste"] else ident["race"]
    print(f"  Name:  {ident['name']}")
    print(f"  Race:  {race_caste}")
    print(f"  Born:  year {ident['birth_year']}    Died: {death_str}")
    if ident["associated_type"]:
        print(f"  Type:  {ident['associated_type']}")

    # -- Status --
    flags: list[str] = []
    if status["deity"]:
        flags.append("Deity")
    if status["force"]:
        flags.append("Force")
    if flags or status["spheres"] or status["active_interactions"]:
        print(_section("Status"))
        if flags:
            print(f"  Flags: {', '.join(flags)}")
        if status["spheres"]:
            print(f"  Spheres: {', '.join(status['spheres'])}")
        if status["active_interactions"]:
            print(f"  Active interactions: {', '.join(status['active_interactions'])}")

    # -- Entity memberships --
    memberships = profile["entity_memberships"]
    if memberships["current"] or memberships["former"]:
        print(_section("Entity Memberships"))
        if memberships["current"]:
            print("  Current:")
            for m in memberships["current"]:
                print(f"    [{m['link_type']}] {m['entity_name']}")
        if memberships["former"]:
            print("  Former:")
            for m in memberships["former"]:
                print(f"    [{m['link_type']}] {m['entity_name']}")

    # -- Positions --
    positions = profile["positions"]
    if positions["current"] or positions["former"]:
        print(_section("Positions Held"))
        if positions["current"]:
            print("  Current:")
            for p in positions["current"]:
                print(f"    {p['entity_name']} (position #{p['position_id']}) — from year {p['start_year']}")
        if positions["former"]:
            print("  Former:")
            for p in positions["former"]:
                print(f"    {p['entity_name']} (position #{p['position_id']}) — year {p['start_year']} to {p['end_year']}")

    # -- Top skills --
    skills = profile["top_skills"]
    if skills:
        print(_section("Top Skills"))
        for sk in skills:
            print(f"  {sk['skill']}: {sk['level']} ({sk['total_ip']} points)")

    # -- Family --
    family = profile["family"]
    if family:
        print(_section("Family"))
        for f in family:
            print(f"  {f['relationship']}: {f['name']} ({f['race']}) [{f['status']}]")

    # -- Artifacts --
    artifacts = profile["artifacts"]
    if artifacts:
        print(_section("Artifacts Held"))
        for a in artifacts:
            print(f"  #{a['id']}: {a['name']}")

    # -- Goals --
    goals = profile["goals"]
    if goals:
        print(_section("Goals"))
        for g in goals:
            print(f"  - {g}")

    # -- Event summary --
    ev_summary = profile["event_summary"]
    if ev_summary:
        print(_section("Event Summary (top types)"))
        for es in ev_summary:
            print(f"  {es['event_type']}: {es['count']}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and display a historical-figure profile."""
    configure_output()
    ap = argparse.ArgumentParser(
        description="Display a comprehensive profile for a Dwarf Fortress historical figure.",
    )
    ap.add_argument(
        "name",
        type=str,
        help="Name (partial, case-insensitive) or numeric HF ID.",
    )
    ap.add_argument(
        "--race",
        type=str,
        default=None,
        help="Filter matches to this race (e.g. DWARF). Case-insensitive.",
    )
    add_common_args(ap)
    args = ap.parse_args()

    # Resolve year range
    year_from: int | None = args.year_from
    year_to: int | None = args.year_to
    if args.year is not None:
        year_from = args.year
        year_to = args.year

    with get_parser_from_args(args) as parser:
        # Resolve the figure(s)
        if args.name.isdigit():
            hf = parser.hf_map.get(args.name)
            if hf is None:
                print(f"No historical figure with ID {args.name}.", file=sys.stderr)
                sys.exit(1)
            matches = [hf]
        else:
            matches = parser.find_hf_by_name(args.name)

        # Apply race filter
        if args.race:
            race_filter = args.race.lower()
            matches = [
                m for m in matches
                if (m.get("race") or "").lower() == race_filter
            ]

        if not matches:
            print(f"No historical figures matching '{args.name}'.", file=sys.stderr)
            sys.exit(1)

        if len(matches) > 1:
            print(f"'{args.name}' matches {len(matches)} figures. Be more specific, or use --race to filter.\n")
            for m in matches:
                hf_id = m.get("id", "?")
                print(f"  [{hf_id}] {format_hf_summary(m, parser)}")
            sys.exit(1)

        # Single match — build and display
        hf = matches[0]
        profile = build_profile(hf, parser, year_from=year_from, year_to=year_to)

        if args.json:
            print_json(profile)
        else:
            print_profile(profile)


if __name__ == "__main__":
    main()
