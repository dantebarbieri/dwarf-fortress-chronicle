"""
site.py — Site/fortress profile from DF Legends XML.

Displays site overview, structures, owning entities, notable residents,
artifacts, and event timeline for a named fortress or site.

Usage:
    python scripts/site.py luregold
    python scripts/site.py 42 --json
    python scripts/site.py luregold --events --year-from 100
    python scripts/site.py luregold --structures --residents
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
    event_involves_site,
    format_hf_summary,
    format_year,
    get_parser_from_args,
    print_json,
)


# ---------------------------------------------------------------------------
# Profile building
# ---------------------------------------------------------------------------


def _build_overview(site: dict[str, Any]) -> dict[str, Any]:
    """Extract basic identity fields for the site."""
    return {
        "id": str(site.get("id", "")),
        "name": (site.get("name") or "Unnamed").title(),
        "type": (site.get("type") or "unknown").replace("_", " ").title(),
        "coords": site.get("coords", ""),
    }


def _build_structures(site: dict[str, Any], parser: LegendsParser) -> list[dict[str, Any]]:
    """Return structures defined at this site."""
    structures: list[dict[str, Any]] = []
    for s in site.get("structures", []):
        entry: dict[str, Any] = {
            "id": str(s.get("id", "")),
            "name": (s.get("name") or "").title() or None,
            "type": (s.get("type") or "unknown").replace("_", " ").title(),
        }
        # Some structures reference an entity owner
        ent_id = s.get("entity_id")
        if ent_id:
            entry["entity_id"] = str(ent_id)
            entry["entity_name"] = parser.get_entity_name(str(ent_id))
        deity_id = s.get("deity")
        if deity_id:
            entry["deity"] = parser.get_hf_name(str(deity_id))
        religion_id = s.get("religion")
        if religion_id:
            entry["religion"] = parser.get_entity_name(str(religion_id))
        structures.append(entry)
    return structures


def _build_owning_entities(
    site_id: str,
    parser: LegendsParser,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """Identify entities connected to this site via ownership events."""
    events = parser.get_site_events(site_id, year_from=year_from, year_to=year_to)
    ownership_types = {
        "created site", "site taken over", "reclaim site",
        "entity primary criminals", "entity relocate",
    }
    seen: dict[str, dict[str, Any]] = {}
    for ev in events:
        if ev.get("type") in ownership_types:
            ent_id = str(ev.get("civ_id") or ev.get("entity_id") or ev.get("attacker_civ_id") or "")
            if not ent_id:
                continue
            entry = {
                "entity_id": ent_id,
                "entity_name": parser.get_entity_name(ent_id),
                "event_type": ev["type"],
                "year": format_year(ev.get("year")),
            }
            seen[ent_id] = entry
    # Also check site_map for any explicit owner/civ fields
    site = parser.site_map.get(site_id, {})
    for key in ("civ_id", "cur_owner_id"):
        eid = site.get(key)
        if eid and str(eid) not in seen:
            seen[str(eid)] = {
                "entity_id": str(eid),
                "entity_name": parser.get_entity_name(str(eid)),
                "event_type": "current_owner",
                "year": "present",
            }
    return list(seen.values())


def _build_residents(
    site_id: str,
    parser: LegendsParser,
) -> list[dict[str, str]]:
    """Find HFs linked to this site via site_links or settlement events."""
    residents: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for hf_id, hf in parser.hf_map.items():
        for sl in hf.get("site_links", []):
            if str(sl.get("site_id", "")) == site_id:
                if hf_id not in seen_ids:
                    seen_ids.add(hf_id)
                    residents.append({
                        "hf_id": hf_id,
                        "summary": format_hf_summary(hf, parser),
                        "link_type": sl.get("link_type", "unknown"),
                    })
    return residents


def _build_artifacts(
    site_id: str,
    parser: LegendsParser,
) -> list[dict[str, str]]:
    """Find artifacts located at or created at this site."""
    artifacts: list[dict[str, str]] = []
    for aid, art in parser.artifact_map.items():
        if str(art.get("site_id", "")) == site_id:
            artifacts.append({
                "id": str(aid),
                "name": (art.get("name") or art.get("name_string") or "Unknown").title(),
            })
    return artifacts


def _build_event_summary(
    site_id: str,
    parser: LegendsParser,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """Count events by type at this site; return sorted by frequency."""
    events = parser.get_site_events(site_id, year_from=year_from, year_to=year_to)
    counts: Counter[str] = Counter()
    for ev in events:
        counts[ev.get("type", "unknown")] += 1
    return [
        {"event_type": etype, "count": cnt}
        for etype, cnt in counts.most_common()
    ]


def _build_event_timeline(
    site_id: str,
    parser: LegendsParser,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    """Build a chronological event list with human-readable descriptions."""
    events = parser.get_site_events(site_id, year_from=year_from, year_to=year_to)
    timeline: list[dict[str, Any]] = []
    for ev in events:
        entry: dict[str, Any] = {
            "year": format_year(ev.get("year")),
            "type": ev.get("type", "unknown"),
            "description": _describe_event(ev, parser),
        }
        timeline.append(entry)
    return timeline


def _describe_event(ev: dict[str, Any], parser: LegendsParser) -> str:
    """Produce a one-line human-readable description for an event."""
    etype = ev.get("type", "unknown")
    year = format_year(ev.get("year"))

    # Resolve common fields lazily
    def hf(key: str) -> str:
        val = ev.get(key)
        return parser.get_hf_name(str(val)) if val else ""

    def ent(key: str) -> str:
        val = ev.get(key)
        return parser.get_entity_name(str(val)) if val else ""

    def site(key: str) -> str:
        val = ev.get(key)
        return parser.get_site_name(str(val)) if val else ""

    # Event-specific templates
    if etype == "hf_died":
        return f"{hf('hfid')} died (cause: {ev.get('death_cause', 'unknown')})"
    if etype == "created site":
        return f"{ent('civ_id')} founded {site('site_id')}"
    if etype == "site taken over":
        return f"Site taken over by {ent('attacker_civ_id')}"
    if etype == "reclaim site":
        return f"{ent('civ_id')} reclaimed the site"
    if etype == "change_hf_state":
        return f"{hf('hfid')} changed state to {ev.get('state', '?')} ({ev.get('reason', '')})"
    if etype == "add_hf_site_link":
        return f"{hf('hfid')} linked to site (type: {ev.get('link_type', '?')})"
    if etype == "created_structure":
        return f"{ent('civ_id')} created structure #{ev.get('structure_id', '?')}"
    if etype == "hf_simple_battle_event":
        return f"{hf('group_1_hfid')} fought {hf('group_2_hfid')}"
    if etype == "artifact_created":
        return f"Artifact #{ev.get('artifact_id', '?')} created by {hf('hfid')}"
    if etype == "item_stolen":
        return f"Item stolen by {hf('hfid')}"
    if etype == "hf_new_pet":
        return f"{hf('group_hfid')} acquired a new pet"
    if etype in ("add_hf_entity_link", "remove_hf_entity_link"):
        return f"{hf('hfid')} {'joined' if etype.startswith('add') else 'left'} {ent('civ_id')}"
    if etype == "creature_devoured":
        return f"Creature devoured by {hf('hfid')}"
    if etype == "hist_figure_reach_summit":
        return f"{hf('hfid')} reached a summit"
    if etype == "change_hf_job":
        return f"{hf('hfid')} changed job"

    # Fallback: show type + any HF/entity references
    parts = [etype.replace("_", " ")]
    for key in ("hfid", "slayer_hfid", "group_hfid"):
        name = hf(key)
        if name:
            parts.append(name)
    return " — ".join(parts)


def build_site_profile(
    site: dict[str, Any],
    parser: LegendsParser,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    include_structures: bool = False,
    include_residents: bool = False,
    include_events: bool = False,
) -> dict[str, Any]:
    """Assemble the full profile dict for a site."""
    site_id = str(site.get("id", ""))
    profile: dict[str, Any] = {
        "overview": _build_overview(site),
        "structures": _build_structures(site, parser),
        "owning_entities": _build_owning_entities(site_id, parser, year_from, year_to),
        "artifacts": _build_artifacts(site_id, parser),
        "event_summary": _build_event_summary(site_id, parser, year_from, year_to),
    }
    if include_structures:
        # Already included by default; flag kept for JSON completeness
        pass
    if include_residents:
        profile["residents"] = _build_residents(site_id, parser)
    if include_events:
        profile["event_timeline"] = _build_event_timeline(
            site_id, parser, year_from, year_to,
        )
    return profile


# ---------------------------------------------------------------------------
# Human-readable output
# ---------------------------------------------------------------------------


def _section(title: str) -> str:
    return f"\n{'=' * 60}\n  {title}\n{'=' * 60}"


def print_site_profile(
    profile: dict[str, Any],
    *,
    show_structures: bool = False,
    show_residents: bool = False,
    show_events: bool = False,
) -> None:
    """Print a site profile dict in human-readable format."""
    ov = profile["overview"]

    # -- Overview --
    print(_section("Site Overview"))
    print(f"  Name:   {ov['name']}")
    print(f"  ID:     {ov['id']}")
    print(f"  Type:   {ov['type']}")
    if ov.get("coords"):
        print(f"  Coords: {ov['coords']}")

    # -- Structures --
    structures = profile.get("structures", [])
    if structures and show_structures:
        print(_section("Structures"))
        for s in structures:
            name_part = f" — {s['name']}" if s.get("name") else ""
            print(f"  #{s['id']}: {s['type']}{name_part}")
            if s.get("entity_name"):
                print(f"        Owner: {s['entity_name']}")
            if s.get("deity"):
                print(f"        Deity: {s['deity']}")
            if s.get("religion"):
                print(f"        Religion: {s['religion']}")
    elif structures:
        print(f"\n  Structures: {len(structures)} (use --structures for details)")

    # -- Owning Entities --
    owners = profile.get("owning_entities", [])
    if owners:
        print(_section("Owning Entities"))
        for o in owners:
            print(f"  {o['entity_name']} (#{o['entity_id']}) — {o['event_type']} (year {o['year']})")

    # -- Residents --
    residents = profile.get("residents", [])
    if residents and show_residents:
        print(_section(f"Notable Residents ({len(residents)})"))
        for r in residents:
            print(f"  [{r['link_type']}] {r['summary']}")
    elif "residents" not in profile:
        pass  # Not requested
    elif not residents:
        print(f"\n  Notable Residents: none found")

    # -- Artifacts --
    artifacts = profile.get("artifacts", [])
    if artifacts:
        print(_section("Artifacts"))
        for a in artifacts:
            print(f"  #{a['id']}: {a['name']}")

    # -- Event summary --
    ev_summary = profile.get("event_summary", [])
    if ev_summary:
        print(_section("Event Summary"))
        for es in ev_summary:
            print(f"  {es['event_type']}: {es['count']}")

    # -- Event timeline --
    timeline = profile.get("event_timeline", [])
    if timeline and show_events:
        print(_section(f"Event Timeline ({len(timeline)} events)"))
        for t in timeline:
            print(f"  [{t['year']}] {t['type']}: {t['description']}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and display a site/fortress profile."""
    configure_output()
    ap = argparse.ArgumentParser(
        description="Display a site/fortress profile from Dwarf Fortress Legends XML.",
    )
    ap.add_argument(
        "name",
        type=str,
        help="Site name (partial, case-insensitive) or numeric site ID.",
    )
    ap.add_argument(
        "--structures",
        action="store_true",
        default=False,
        help="Show structure details.",
    )
    ap.add_argument(
        "--residents",
        action="store_true",
        default=False,
        help="Show HFs linked to this site.",
    )
    ap.add_argument(
        "--events",
        action="store_true",
        default=False,
        help="Show chronological event timeline.",
    )
    add_common_args(ap)
    args = ap.parse_args()

    # Resolve year range
    year_from: int | None = args.year_from
    year_to: int | None = args.year_to
    if args.year is not None:
        year_from = args.year
        year_to = args.year

    # If year filters are given, implicitly enable event timeline
    show_events: bool = args.events or (year_from is not None or year_to is not None)

    with get_parser_from_args(args) as parser:
        # Resolve the site
        if args.name.isdigit():
            site = parser.site_map.get(args.name)
            if site is None:
                print(f"No site with ID {args.name}.", file=sys.stderr)
                sys.exit(1)
            matches = [site]
        else:
            matches = parser.find_site_by_name(args.name)

        if not matches:
            print(f"No sites matching '{args.name}'.", file=sys.stderr)
            sys.exit(1)

        if len(matches) > 1:
            print(
                f"'{args.name}' matches {len(matches)} sites. "
                "Be more specific or use a numeric ID.\n",
            )
            for m in matches:
                sid = m.get("id", "?")
                sname = (m.get("name") or "Unnamed").title()
                stype = (m.get("type") or "unknown").replace("_", " ")
                print(f"  [{sid}] {sname} ({stype})")
            sys.exit(1)

        # Single match — build and display
        site = matches[0]
        profile = build_site_profile(
            site,
            parser,
            year_from=year_from,
            year_to=year_to,
            include_structures=args.structures,
            include_residents=args.residents,
            include_events=show_events,
        )

        if args.json:
            print_json(profile)
        else:
            print_site_profile(
                profile,
                show_structures=args.structures,
                show_residents=args.residents,
                show_events=show_events,
            )


if __name__ == "__main__":
    main()
