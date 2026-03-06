"""
creature.py — Look up a specific creature / historical figure by name
and display everything the Legends XML knows about them.

Usage:
    python scripts/creature.py "atir"
    python scripts/creature.py 12345 --events --kills
    python scripts/creature.py "goblin" --list --json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Allow running from the DF root directory:  python scripts/creature.py …
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.legends_parser import (
    LegendsParser,
    add_common_args,
    configure_output,
    event_involves_hf,
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


def _print_bio(hf: dict[str, Any], parser: LegendsParser) -> None:
    """Print biographical summary."""
    _section("Biography")
    name = (hf.get("name") or "Unnamed").title()
    race = (hf.get("race") or "unknown").replace("_", " ").title()
    caste = (hf.get("caste") or "").replace("_", " ").title()
    print(f"  Name:  {name}")
    print(f"  Race:  {race}{f' ({caste})' if caste else ''}")
    print(f"  ID:    {hf.get('id', '?')}")
    print(f"  Born:  year {format_year(hf.get('birth_year'))}")
    print(f"  Died:  year {format_year(hf.get('death_year'))}")
    if hf.get("associated_type"):
        print(f"  Type:  {hf['associated_type']}")
    if hf.get("deity"):
        print("  Deity: yes")
    if hf.get("force"):
        print("  Force: yes")
    spheres = hf.get("spheres")
    if spheres:
        if isinstance(spheres, list):
            print(f"  Spheres: {', '.join(spheres)}")
        else:
            print(f"  Spheres: {spheres}")
    goals = hf.get("goals")
    if goals:
        if isinstance(goals, list):
            print(f"  Goals: {', '.join(goals)}")
        else:
            print(f"  Goals: {goals}")


def _print_entity_affiliations(hf: dict[str, Any], parser: LegendsParser) -> None:
    """Print entity links (memberships, enemies, etc.)."""
    links = hf.get("entity_links", [])
    if not links:
        return
    _section("Entity Affiliations")
    for link in links:
        eid = link.get("entity_id", "?")
        ename = parser.get_entity_name(eid)
        ltype = link.get("link_type", "?")
        strength = link.get("link_strength", "")
        extra = f"  (strength {strength})" if strength else ""
        print(f"  [{ltype}] {ename} (id {eid}){extra}")


def _print_positions(hf: dict[str, Any], parser: LegendsParser) -> None:
    """Print current and former position links."""
    current = hf.get("entity_position_links", [])
    former = hf.get("entity_former_position_links", [])
    if not current and not former:
        return
    _section("Positions")
    if current:
        print("  Current:")
        for pos in current:
            eid = pos.get("entity_id", "?")
            ename = parser.get_entity_name(eid)
            pid = pos.get("position_profile_id", "?")
            start = pos.get("start_year", "?")
            print(f"    {ename} — position {pid}, since year {start}")
    if former:
        print("  Former:")
        for pos in former:
            eid = pos.get("entity_id", "?")
            ename = parser.get_entity_name(eid)
            pid = pos.get("position_profile_id", "?")
            start = pos.get("start_year", "?")
            end = pos.get("end_year", "?")
            print(f"    {ename} — position {pid}, years {start}–{end}")


def _print_relationships(hf: dict[str, Any], parser: LegendsParser) -> None:
    """Print HF-to-HF links (family, companions, deities, etc.)."""
    links = hf.get("hf_links", [])
    if not links:
        return
    _section("Relationships")
    for link in links:
        hfid = link.get("hfid", "?")
        name = parser.get_hf_name(hfid)
        ltype = link.get("link_type", "?")
        print(f"  [{ltype}] {name} (id {hfid})")


def _print_skills(hf: dict[str, Any]) -> None:
    """Print skills sorted by IP descending."""
    skills = hf.get("hf_skills", [])
    if not skills:
        return
    _section("Skills")
    sorted_skills = sorted(
        skills,
        key=lambda s: int(s.get("total_ip", 0)),
        reverse=True,
    )
    for sk in sorted_skills:
        skill_name = (sk.get("skill") or "?").replace("_", " ").title()
        ip = int(sk.get("total_ip", 0))
        level = skill_level_name(ip)
        print(f"  {skill_name:30s}  {level:16s}  (IP {ip})")


def _print_held_artifacts(hf: dict[str, Any], parser: LegendsParser) -> None:
    """Print artifacts held by this figure."""
    held = hf.get("holds_artifact")
    if not held:
        return
    _section("Held Artifacts")
    if isinstance(held, str):
        held = [held]
    for aid in held:
        art = parser.artifact_map.get(str(aid))
        if art:
            aname = (art.get("name") or art.get("name_string") or "unnamed").title()
            item = art.get("item_type") or art.get("item_subtype") or ""
            print(f"  {aname} (id {aid}) {item}")
        else:
            print(f"  Artifact id {aid}")


def _get_kills(hf_id: str, parser: LegendsParser) -> list[dict[str, Any]]:
    """Extract kill records: events where this figure is the slayer."""
    kills: list[dict[str, Any]] = []
    target = str(hf_id)
    for ev in parser.events:
        if ev.get("type") != "hf died":
            continue
        if str(ev.get("slayer_hfid", "")) != target:
            continue
        victim_id = ev.get("hfid") or ev.get("hfid2") or "?"
        victim_hf = parser.hf_map.get(str(victim_id))
        victim_name = (victim_hf.get("name") or "unnamed").title() if victim_hf else f"Unknown ({victim_id})"
        victim_race = (victim_hf.get("race") or "?").replace("_", " ").title() if victim_hf else "?"
        kills.append({
            "year": ev.get("year", "?"),
            "victim_id": victim_id,
            "victim_name": victim_name,
            "victim_race": victim_race,
            "cause": ev.get("death_cause") or ev.get("cause") or "?",
            "site_id": ev.get("site_id"),
        })
    return kills


def _print_kills(hf_id: str, parser: LegendsParser) -> None:
    """Print kill list."""
    kills = _get_kills(hf_id, parser)
    _section(f"Kill Count ({len(kills)})")
    if not kills:
        print("  No recorded kills.")
        return
    for k in kills:
        site_str = ""
        if k["site_id"]:
            site_str = f" at {parser.get_site_name(k['site_id'])}"
        print(f"  Year {k['year']:>5s}  {k['victim_name']} ({k['victim_race']}){site_str}")


def _print_events(hf_id: str, parser: LegendsParser, args: argparse.Namespace) -> None:
    """Print chronological event timeline for this figure."""
    year_from = args.year if args.year else args.year_from
    year_to = args.year if args.year else args.year_to
    events = parser.get_hf_events(hf_id, year_from=year_from, year_to=year_to)
    _section(f"Event Timeline ({len(events)} events)")
    if not events:
        print("  No events in range.")
        return
    for ev in events:
        yr = ev.get("year", "?")
        etype = ev.get("type", "?")
        # Build a compact info string from notable fields
        parts: list[str] = [f"[{etype}]"]
        if ev.get("site_id"):
            parts.append(f"site={parser.get_site_name(ev['site_id'])}")
        if ev.get("hfid") and str(ev["hfid"]) != str(hf_id):
            parts.append(f"hf={parser.get_hf_name(ev['hfid'])}")
        if ev.get("hfid2") and str(ev["hfid2"]) != str(hf_id):
            parts.append(f"hf2={parser.get_hf_name(ev['hfid2'])}")
        if ev.get("slayer_hfid") and str(ev["slayer_hfid"]) != str(hf_id):
            parts.append(f"slayer={parser.get_hf_name(ev['slayer_hfid'])}")
        if ev.get("civ_id"):
            parts.append(f"civ={parser.get_entity_name(ev['civ_id'])}")
        print(f"  Year {yr:>5s}  {' '.join(parts)}")


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def _build_json_output(
    hf: dict[str, Any],
    parser: LegendsParser,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Build a JSON-serializable dict with all requested data."""
    hf_id = str(hf["id"])
    data: dict[str, Any] = {"figure": hf}
    # Resolve entity names in links
    for link in hf.get("entity_links", []):
        link["entity_name"] = parser.get_entity_name(link.get("entity_id", ""))
    for link in hf.get("hf_links", []):
        link["hf_name"] = parser.get_hf_name(link.get("hfid", ""))
    # Resolve held artifact names
    held = hf.get("holds_artifact")
    if held:
        artifact_list = [held] if isinstance(held, str) else held
        data["held_artifacts"] = [
            parser.artifact_map.get(str(aid), {"id": aid}) for aid in artifact_list
        ]
    if args.kills:
        data["kills"] = _get_kills(hf_id, parser)
    if args.events:
        year_from = args.year if args.year else args.year_from
        year_to = args.year if args.year else args.year_to
        data["events"] = parser.get_hf_events(hf_id, year_from=year_from, year_to=year_to)
    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for creature CLI."""
    configure_output()
    ap = argparse.ArgumentParser(
        description="Look up a creature / historical figure in the Legends XML.",
    )
    ap.add_argument(
        "name",
        type=str,
        help="Creature name or numeric ID (partial match allowed).",
    )
    add_common_args(ap)
    ap.add_argument(
        "--events",
        action="store_true",
        default=False,
        help="Show full event timeline for the figure.",
    )
    ap.add_argument(
        "--kills",
        action="store_true",
        default=False,
        help="Show kill list (victims slain by this figure).",
    )
    ap.add_argument(
        "--list",
        action="store_true",
        default=False,
        dest="list_all",
        help="If the name matches multiple figures, list all summaries instead of erroring.",
    )
    args = ap.parse_args()

    with get_parser_from_args(args) as parser:
        # Resolve by ID or name
        if args.name.isdigit():
            hf = parser.hf_map.get(args.name)
            if not hf:
                print(f"No historical figure with ID {args.name}.", file=sys.stderr)
                sys.exit(1)
            matches = [hf]
        else:
            matches = parser.find_hf_by_name(args.name)

        if not matches:
            print(f"No historical figures matching '{args.name}'.", file=sys.stderr)
            sys.exit(1)

        # Ambiguous match handling
        if len(matches) > 1 and not args.list_all:
            print(f"'{args.name}' matches {len(matches)} figures. "
                  f"Use --list to show all, or be more specific:\n")
            for m in matches[:25]:
                print(f"  {format_hf_summary(m, parser)}  (id {m.get('id', '?')})")
            if len(matches) > 25:
                print(f"  … and {len(matches) - 25} more.")
            sys.exit(1)

        # --list mode: show summaries for all matches
        if len(matches) > 1 and args.list_all:
            if args.json:
                print_json([
                    {"id": m.get("id"), "summary": format_hf_summary(m, parser)}
                    for m in matches
                ])
            else:
                print(f"Found {len(matches)} matches for '{args.name}':\n")
                for m in matches:
                    print(f"  {format_hf_summary(m, parser)}  (id {m.get('id', '?')})")
            return

        # Single figure output
        hf = matches[0]
        hf_id = str(hf["id"])

        if args.json:
            print_json(_build_json_output(hf, parser, args))
            return

        print(f"\n{'═' * 60}")
        print(f"  {format_hf_summary(hf, parser)}")
        print(f"{'═' * 60}")

        _print_bio(hf, parser)
        _print_entity_affiliations(hf, parser)
        _print_positions(hf, parser)
        _print_relationships(hf, parser)
        _print_skills(hf)
        _print_held_artifacts(hf, parser)

        if args.kills:
            _print_kills(hf_id, parser)

        if args.events:
            _print_events(hf_id, parser, args)

        print()


if __name__ == "__main__":
    main()
