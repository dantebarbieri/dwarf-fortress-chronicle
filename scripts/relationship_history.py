#!/usr/bin/env python3
"""Shared relationship and interaction history between two or more historical figures.

Use cases:
  - Understanding bonds between dwarves (friends, family, colleagues)
  - Profiling a goblin squad (shared entity, shared battles)
  - Tracing why a migrant arrived without family (find kin, check events)

Examples:
  python scripts/relationship_history.py "atir" "unib"
  python scripts/relationship_history.py 1234 5678 9012
  python scripts/relationship_history.py "atir" "unib" --events --year-from 100
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

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
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event_sort_key(event: dict) -> tuple[int, int]:
    """Sort key for chronological ordering of events."""
    try:
        year = int(event.get("year", 0))
    except (TypeError, ValueError):
        year = 0
    try:
        seconds = int(event.get("seconds72", 0))
    except (TypeError, ValueError):
        seconds = 0
    return (year, seconds)


def _link_type_label(link_type: str) -> str:
    """Pretty-print a link_type value."""
    return link_type.replace("_", " ").strip()


def _describe_event(event: dict, parser: LegendsParser, subject_ids: set[str]) -> str:
    """Return a human-readable one-liner for an event, highlighting subjects."""
    etype = event.get("type", "unknown event")
    year = format_year(event.get("year"))
    parts: list[str] = [f"Year {year}"]

    sec = event.get("seconds72")
    if sec and str(sec) != "-1":
        parts[0] += f" (t={sec})"

    parts.append(etype)

    # Build a role→name mapping for subjects found in this event
    roles: list[str] = []
    for field in ("hfid", "hfid1", "hfid2", "slayer_hfid", "woundee_hfid",
                  "wounder_hfid", "snatcher_hfid", "victim_hfid",
                  "doer_hfid", "target_hfid", "seeker_hfid",
                  "giver_hist_figure_id", "receiver_hist_figure_id",
                  "hist_fig_id", "hist_figure_id", "group_hfid",
                  "attacker_hfid", "defender_hfid"):
        val = event.get(field)
        if val and str(val) in subject_ids:
            name = parser.get_hf_name(str(val))
            label = field.replace("_hfid", "").replace("_hist_figure_id", "").replace("hfid", "figure").replace("_", " ")
            roles.append(f"{name} ({label})")

    if roles:
        parts.append("— " + ", ".join(roles))

    # Site context
    site_id = event.get("site_id") or event.get("site")
    if site_id:
        parts.append(f"at {parser.get_site_name(str(site_id))}")

    return "  ".join(parts)


EVENT_DESCRIPTIONS: dict[str, str] = {
    "hf died": "death",
    "hf simple battle event": "battle",
    "add hf hf link": "relationship formed",
    "remove hf hf link": "relationship ended",
    "hf relationship denied": "relationship denied",
    "hf reunion": "reunion",
    "change hf state": "state change",
    "hf wounded": "wounding",
    "hf abducted": "abduction",
    "artifact created": "artifact creation",
    "artifact given": "artifact exchange",
    "hf travel": "travel",
    "hf new pet": "gained pet",
    "change hf job": "job change",
    "add hf entity link": "joined entity",
    "remove hf entity link": "left entity",
    "hf gains secret goal": "secret goal",
    "hf profaned structure": "profaned structure",
    "hf confronted": "confrontation",
    "hf does interaction": "interaction",
    "assume identity": "assumed identity",
    "create entity position": "position created",
    "creature devoured": "devoured",
    "hf learns secret": "learned secret",
}


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def resolve_subjects(parser: LegendsParser, names: list[str]) -> list[dict]:
    """Resolve each name/id to an HF dict. Exits on ambiguity."""
    subjects: list[dict] = []
    for name in names:
        # Try numeric ID first
        if name.isdigit():
            hf = parser.hf_map.get(name)
            if hf is None:
                print(f"Error: no historical figure with ID {name}", file=sys.stderr)
                sys.exit(1)
            subjects.append(hf)
            continue

        matches = parser.find_hf_by_name(name)
        if len(matches) == 0:
            print(f"Error: no historical figure matching '{name}'", file=sys.stderr)
            sys.exit(1)
        elif len(matches) == 1:
            subjects.append(matches[0])
        else:
            print(f"Error: '{name}' is ambiguous — {len(matches)} matches:", file=sys.stderr)
            for m in matches[:15]:
                print(f"  ID {m['id']}: {format_hf_summary(m, parser)}", file=sys.stderr)
            if len(matches) > 15:
                print(f"  ... and {len(matches) - 15} more", file=sys.stderr)
            sys.exit(1)
    return subjects


def find_direct_relationships(subjects: list[dict]) -> list[dict]:
    """Find hf_links between any pair of subjects."""
    id_set = {str(s["id"]) for s in subjects}
    name_map = {str(s["id"]): s.get("name", f'ID {s["id"]}') for s in subjects}
    results: list[dict] = []

    for s in subjects:
        sid = str(s["id"])
        for link in s.get("hf_links", []):
            target = str(link.get("hfid", ""))
            if target in id_set and target != sid:
                results.append({
                    "from_id": sid,
                    "from_name": name_map[sid],
                    "to_id": target,
                    "to_name": name_map[target],
                    "link_type": link.get("link_type", "unknown"),
                    "link_strength": link.get("link_strength"),
                })
    return results


def find_shared_entities(subjects: list[dict], parser: LegendsParser) -> list[dict]:
    """Find entities where 2+ subjects share membership."""
    # Map entity_id → list of (subject_id, link_type, link details)
    entity_members: dict[str, list[dict]] = defaultdict(list)

    for s in subjects:
        sid = str(s["id"])
        sname = s.get("name", f'ID {s["id"]}')

        for link in s.get("entity_links", []):
            eid = str(link.get("entity_id", ""))
            if eid:
                entry: dict[str, Any] = {
                    "hf_id": sid,
                    "hf_name": sname,
                    "link_type": link.get("link_type", "unknown"),
                }
                entity_members[eid].append(entry)

        # Also check position links
        for link in s.get("entity_position_links", []):
            eid = str(link.get("entity_id", ""))
            if eid:
                entry = {
                    "hf_id": sid,
                    "hf_name": sname,
                    "link_type": "position",
                    "position_id": link.get("position_profile_id"),
                }
                entity_members[eid].append(entry)

        for link in s.get("entity_former_position_links", []):
            eid = str(link.get("entity_id", ""))
            if eid:
                entry = {
                    "hf_id": sid,
                    "hf_name": sname,
                    "link_type": "former position",
                    "position_id": link.get("position_profile_id"),
                }
                entity_members[eid].append(entry)

    shared: list[dict] = []
    for eid, members in entity_members.items():
        unique_hfs = {m["hf_id"] for m in members}
        if len(unique_hfs) >= 2:
            shared.append({
                "entity_id": eid,
                "entity_name": parser.get_entity_name(eid),
                "members": members,
            })
    return shared


def find_shared_sites(subjects: list[dict], parser: LegendsParser) -> list[dict]:
    """Find sites where 2+ subjects have connections via site_links."""
    site_connections: dict[str, list[dict]] = defaultdict(list)

    for s in subjects:
        sid = str(s["id"])
        sname = s.get("name", f'ID {s["id"]}')
        for link in s.get("site_links", []):
            site_id = str(link.get("site_id", link.get("site", "")))
            if site_id:
                site_connections[site_id].append({
                    "hf_id": sid,
                    "hf_name": sname,
                    "link_type": link.get("link_type", link.get("type", "unknown")),
                })

    shared: list[dict] = []
    for site_id, conns in site_connections.items():
        unique_hfs = {c["hf_id"] for c in conns}
        if len(unique_hfs) >= 2:
            shared.append({
                "site_id": site_id,
                "site_name": parser.get_site_name(site_id),
                "connections": conns,
            })
    return shared


def find_shared_events(
    subjects: list[dict],
    parser: LegendsParser,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict]:
    """Find events involving 2+ subjects. Single pass over all events."""
    subject_ids = {str(s["id"]) for s in subjects}
    shared: list[dict] = []

    for event in parser.events:
        # Year filter
        try:
            eyear = int(event.get("year", 0))
        except (TypeError, ValueError):
            eyear = 0
        if year_from is not None and eyear < year_from:
            continue
        if year_to is not None and eyear > year_to:
            continue

        # Check which subjects are involved
        involved = [sid for sid in subject_ids if event_involves_hf(event, sid)]
        if len(involved) >= 2:
            shared.append({
                "event": event,
                "involved_ids": involved,
            })

    shared.sort(key=lambda x: _event_sort_key(x["event"]))
    return shared


def find_family_path(
    hf_a_id: str,
    hf_b_id: str,
    parser: LegendsParser,
    max_depth: int = 3,
) -> list[dict] | None:
    """BFS through hf_links to find shortest family path between two figures."""
    FAMILY_LINK_TYPES = {
        "spouse", "former spouse", "child", "mother", "father",
        "deity", "master", "apprentice", "companion",
    }

    # BFS state: queue of (current_id, path)
    # path is list of {"hf_id", "link_type", "direction"}
    visited: set[str] = set()
    queue: deque[tuple[str, list[dict]]] = deque()
    queue.append((hf_a_id, []))
    visited.add(hf_a_id)

    while queue:
        current_id, path = queue.popleft()
        if len(path) > max_depth:
            continue

        hf = parser.hf_map.get(current_id)
        if hf is None:
            continue

        for link in hf.get("hf_links", []):
            lt = link.get("link_type", "")
            if lt not in FAMILY_LINK_TYPES:
                continue
            target = str(link.get("hfid", ""))
            if not target or target in visited:
                continue

            new_step = {
                "from_id": current_id,
                "from_name": parser.get_hf_name(current_id),
                "to_id": target,
                "to_name": parser.get_hf_name(target),
                "link_type": lt,
            }
            new_path = path + [new_step]

            if target == hf_b_id:
                return new_path

            if len(new_path) < max_depth:
                visited.add(target)
                queue.append((target, new_path))

    return None


def build_timeline_summary(
    subjects: list[dict],
    shared_events: list[dict],
    shared_entities: list[dict],
    parser: LegendsParser,
) -> list[dict]:
    """Build a brief chronological narrative of key moments."""
    entries: list[dict] = []
    name_map = {str(s["id"]): s.get("name", f'ID {s["id"]}') for s in subjects}

    # Birth events
    for s in subjects:
        by = s.get("birth_year")
        if by is not None:
            try:
                by_int = int(by)
            except (TypeError, ValueError):
                continue
            entries.append({
                "year": by_int,
                "text": f"{s.get('name', 'Unknown')} born",
            })

    # Death events
    for s in subjects:
        dy = s.get("death_year")
        if dy is not None:
            try:
                dy_int = int(dy)
                if dy_int >= 0:
                    entries.append({
                        "year": dy_int,
                        "text": f"{s.get('name', 'Unknown')} died",
                    })
            except (TypeError, ValueError):
                pass

    # Shared entity memberships (approximate — use earliest event year or 0)
    for se in shared_entities:
        names = sorted({m["hf_name"] for m in se["members"]})
        entries.append({
            "year": 0,
            "text": f"{', '.join(names)} share membership in {se['entity_name']}",
            "sort_last": True,
        })

    # Key shared events
    KEY_TYPES = {
        "add hf hf link", "remove hf hf link", "hf died", "hf wounded",
        "hf simple battle event", "hf abducted", "hf reunion",
        "hf relationship denied", "artifact created", "artifact given",
        "add hf entity link", "change hf state",
    }
    for se in shared_events:
        ev = se["event"]
        etype = ev.get("type", "")
        if etype not in KEY_TYPES:
            continue
        try:
            year = int(ev.get("year", 0))
        except (TypeError, ValueError):
            year = 0
        involved_names = [name_map.get(i, i) for i in se["involved_ids"]]
        label = EVENT_DESCRIPTIONS.get(etype, etype)
        entries.append({
            "year": year,
            "text": f"{label}: {', '.join(involved_names)}",
        })

    # Deduplicate very similar entries in the same year
    seen: set[str] = set()
    unique: list[dict] = []
    for e in entries:
        key = f"{e['year']}:{e['text']}"
        if key not in seen:
            seen.add(key)
            unique.append(e)

    unique.sort(key=lambda e: (e["year"], 1 if e.get("sort_last") else 0))
    return unique


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_human(
    subjects: list[dict],
    direct_rels: list[dict],
    shared_entities: list[dict],
    shared_sites: list[dict],
    shared_events: list[dict],
    family_path: list[dict] | None,
    timeline: list[dict],
    parser: LegendsParser,
    show_events: bool = False,
) -> None:
    """Print human-readable analysis."""
    subject_ids = {str(s["id"]) for s in subjects}

    # 1. Subjects
    print_section("Subjects")
    for s in subjects:
        print(f"  {format_hf_summary(s, parser)}")

    # 2. Direct Relationships
    print_section("Direct Relationships")
    if direct_rels:
        for r in direct_rels:
            strength = f" (strength: {r['link_strength']})" if r.get("link_strength") else ""
            print(f"  {r['from_name']}  —[{_link_type_label(r['link_type'])}]→  {r['to_name']}{strength}")
    else:
        print("  No direct hf_links found between these figures.")

    # 3. Shared Entity Memberships
    print_section("Shared Entity Memberships")
    if shared_entities:
        for se in shared_entities:
            print(f"\n  {se['entity_name']} (ID {se['entity_id']}):")
            for m in se["members"]:
                extra = f", position {m['position_id']}" if m.get("position_id") else ""
                print(f"    • {m['hf_name']}: {_link_type_label(m['link_type'])}{extra}")
    else:
        print("  No shared entity memberships found.")

    # 4. Shared Site Connections
    print_section("Shared Site Connections")
    if shared_sites:
        for ss in shared_sites:
            print(f"\n  {ss['site_name']} (ID {ss['site_id']}):")
            for c in ss["connections"]:
                print(f"    • {c['hf_name']}: {_link_type_label(c['link_type'])}")
    else:
        print("  No shared site connections found.")

    # 5. Shared Events
    print_section(f"Shared Events ({len(shared_events)} total)")
    if shared_events:
        # Type summary
        type_counts: dict[str, int] = defaultdict(int)
        for se in shared_events:
            etype = se["event"].get("type", "unknown")
            type_counts[etype] += 1
        print("\n  Event type breakdown:")
        for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            label = EVENT_DESCRIPTIONS.get(etype, etype)
            print(f"    {label} ({etype}): {count}")

        if show_events:
            print("\n  Full timeline:")
            for se in shared_events:
                desc = _describe_event(se["event"], parser, subject_ids)
                print(f"    {desc}")
    else:
        print("  No shared events found.")

    # 6. Family Network (only for 2 figures)
    if len(subjects) == 2:
        print_section("Family Network")
        if family_path:
            print("  Path found:")
            for step in family_path:
                print(f"    {step['from_name']}  —[{_link_type_label(step['link_type'])}]→  {step['to_name']}")
        else:
            print("  No family path found within 3 hops.")

    # 7. Timeline Summary
    print_section("Timeline Summary")
    if timeline:
        for entry in timeline:
            year_str = format_year(str(entry["year"])) if entry["year"] != 0 else "???"
            print(f"  Year {year_str}: {entry['text']}")
    else:
        print("  No timeline events to display.")

    print()


def build_json_output(
    subjects: list[dict],
    direct_rels: list[dict],
    shared_entities: list[dict],
    shared_sites: list[dict],
    shared_events: list[dict],
    family_path: list[dict] | None,
    timeline: list[dict],
    parser: LegendsParser,
) -> dict:
    """Build the full analysis as a JSON-serializable dict."""
    subject_ids = {str(s["id"]) for s in subjects}

    # Subjects summary
    subjects_out = []
    for s in subjects:
        subjects_out.append({
            "id": str(s["id"]),
            "name": s.get("name", "Unknown"),
            "race": s.get("race"),
            "caste": s.get("caste"),
            "birth_year": s.get("birth_year"),
            "death_year": s.get("death_year"),
            "summary": format_hf_summary(s, parser),
        })

    # Shared events — serialize without full event blob
    events_out = []
    for se in shared_events:
        ev = se["event"]
        events_out.append({
            "year": ev.get("year"),
            "seconds72": ev.get("seconds72"),
            "type": ev.get("type"),
            "involved_ids": se["involved_ids"],
            "description": _describe_event(ev, parser, subject_ids),
        })

    # Event type summary
    type_counts: dict[str, int] = defaultdict(int)
    for se in shared_events:
        type_counts[se["event"].get("type", "unknown")] += 1

    return {
        "subjects": subjects_out,
        "direct_relationships": direct_rels,
        "shared_entities": shared_entities,
        "shared_sites": shared_sites,
        "shared_events": {
            "count": len(shared_events),
            "type_breakdown": dict(sorted(type_counts.items(), key=lambda x: -x[1])),
            "events": events_out,
        },
        "family_path": family_path,
        "timeline": timeline,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    configure_output()
    ap = argparse.ArgumentParser(
        description="Show shared relationship and interaction history between historical figures.",
        epilog="Examples:\n"
               '  %(prog)s "atir" "unib"\n'
               "  %(prog)s 1234 5678 9012\n"
               '  %(prog)s "atir" "unib" --events --year-from 100\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "names",
        nargs="+",
        help="Two or more historical figure names or numeric IDs.",
    )
    ap.add_argument(
        "--events",
        action="store_true",
        default=False,
        help="Show full shared event timeline (default: summary only).",
    )
    ap.add_argument(
        "--include-indirect",
        action="store_true",
        default=False,
        help="Include events where one figure affected someone related to the other.",
    )
    add_common_args(ap)
    args = ap.parse_args()

    if len(args.names) < 2:
        ap.error("At least 2 historical figure names or IDs are required.")

    # Year filters from common args
    year_from: int | None = getattr(args, "year_from", None) or getattr(args, "year", None)
    year_to: int | None = getattr(args, "year_to", None) or getattr(args, "year", None)

    with get_parser_from_args(args) as parser:
        # Resolve subjects
        subjects = resolve_subjects(parser, args.names)

        # Core analyses
        direct_rels = find_direct_relationships(subjects)
        shared_entities = find_shared_entities(subjects, parser)
        shared_sites = find_shared_sites(subjects, parser)
        shared_events = find_shared_events(subjects, parser, year_from=year_from, year_to=year_to)

        # Include indirect events if requested
        if args.include_indirect:
            subject_ids = {str(s["id"]) for s in subjects}
            # Collect IDs of figures directly linked to any subject
            related_ids: set[str] = set()
            for s in subjects:
                for link in s.get("hf_links", []):
                    rid = str(link.get("hfid", ""))
                    if rid and rid not in subject_ids:
                        related_ids.add(rid)

            # Find events where one subject acted on a related figure of another
            indirect_events: list[dict] = []
            for event in parser.events:
                try:
                    eyear = int(event.get("year", 0))
                except (TypeError, ValueError):
                    eyear = 0
                if year_from is not None and eyear < year_from:
                    continue
                if year_to is not None and eyear > year_to:
                    continue

                involved_subjects = [sid for sid in subject_ids if event_involves_hf(event, sid)]
                involved_related = [rid for rid in related_ids if event_involves_hf(event, rid)]

                if involved_subjects and involved_related:
                    # Don't duplicate events already in shared_events
                    if len(involved_subjects) < 2:
                        indirect_events.append({
                            "event": event,
                            "involved_ids": involved_subjects + involved_related,
                        })

            indirect_events.sort(key=lambda x: _event_sort_key(x["event"]))
            shared_events = sorted(
                shared_events + indirect_events,
                key=lambda x: _event_sort_key(x["event"]),
            )

        # Family path (only for exactly 2 figures)
        family_path: list[dict] | None = None
        if len(subjects) == 2:
            family_path = find_family_path(
                str(subjects[0]["id"]),
                str(subjects[1]["id"]),
                parser,
            )

        # Timeline summary
        timeline = build_timeline_summary(subjects, shared_events, shared_entities, parser)

        # Output
        if getattr(args, "json", False):
            data = build_json_output(
                subjects, direct_rels, shared_entities, shared_sites,
                shared_events, family_path, timeline, parser,
            )
            print_json(data)
        else:
            print_human(
                subjects, direct_rels, shared_entities, shared_sites,
                shared_events, family_path, timeline, parser,
                show_events=args.events,
            )


if __name__ == "__main__":
    main()
