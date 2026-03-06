"""
events.py — General-purpose event browser/filter for Dwarf Fortress Legends XML.

Browse, search, and summarize world events by type, site, entity, historical
figure, and/or year range.  Output is human-readable by default, or JSON with
``--json``.

Usage examples:
    python scripts/events.py --year 102 --site luregold
    python scripts/events.py --type "hf died" --year-from 100
    python scripts/events.py --types
    python scripts/events.py --figure "atir" --summary
    python scripts/events.py --entity "clinching" --limit 50 --raw
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Ensure the DF root is on sys.path so ``from scripts.legends_parser …`` works
# when the script is invoked directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.legends_parser import (
    LegendsParser,
    add_common_args,
    configure_output,
    event_involves_entity,
    event_involves_hf,
    event_involves_site,
    format_hf_summary,
    format_year,
    get_parser_from_args,
    print_json,
)


# ---------------------------------------------------------------------------
# Human-readable event descriptions
# ---------------------------------------------------------------------------

def _hf_label(hf_id: str | None, parser: LegendsParser) -> str:
    """Short label for a historical figure: 'Name (Race, Caste) [ID: N]'."""
    if hf_id is None or hf_id in ("", "-1"):
        return "unknown"
    hf = parser.hf_map.get(str(hf_id))
    if not hf:
        return f"Unknown [ID: {hf_id}]"
    name = (hf.get("name") or "Unnamed").title()
    race = (hf.get("race") or "?").replace("_", " ").title()
    caste = (hf.get("caste") or "").replace("_", " ").title()
    rc = f"{race}, {caste}" if caste else race
    return f"{name} ({rc}) [ID: {hf_id}]"


def _site_label(site_id: str | None, parser: LegendsParser) -> str:
    if site_id is None or site_id in ("", "-1"):
        return "unknown"
    name = parser.get_site_name(str(site_id))
    return f"{name} [ID: {site_id}]"


def _entity_label(entity_id: str | None, parser: LegendsParser) -> str:
    if entity_id is None or entity_id in ("", "-1"):
        return "unknown"
    name = parser.get_entity_name(str(entity_id))
    return f"{name} [ID: {entity_id}]"


def _artifact_label(art_id: str | None, parser: LegendsParser) -> str:
    if art_id is None or art_id in ("", "-1"):
        return "unknown"
    art = parser.artifact_map.get(str(art_id))
    if art:
        name = (art.get("name") or art.get("name_string") or "unnamed").title()
        return f"{name} [ID: {art_id}]"
    return f"Unknown [ID: {art_id}]"


# -- Per-type describers ---------------------------------------------------

def _describe_hf_died(ev: dict, p: LegendsParser) -> str:
    victim = _hf_label(ev.get("hfid"), p)
    slayer = _hf_label(ev.get("slayer_hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    cause = ev.get("cause", "unknown cause")
    parts = [f"{victim} was killed"]
    if ev.get("slayer_hfid") and ev["slayer_hfid"] != "-1":
        parts.append(f"by {slayer}")
    if ev.get("site_id") and ev["site_id"] != "-1":
        parts.append(f"at {site}")
    parts.append(f"(cause: {cause})")
    return " ".join(parts)


def _describe_artifact_created(ev: dict, p: LegendsParser) -> str:
    creator = _hf_label(ev.get("hfid"), p)
    artifact = _artifact_label(ev.get("artifact_id"), p)
    site = _site_label(ev.get("site_id"), p)
    parts = [f"{creator} created artifact {artifact}"]
    if ev.get("site_id") and ev["site_id"] != "-1":
        parts.append(f"at {site}")
    return " ".join(parts)


def _describe_change_hf_state(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("hfid"), p)
    state = ev.get("state", "?")
    site = _site_label(ev.get("site_id"), p)
    parts = [f"{hf} [{state}]"]
    if ev.get("site_id") and ev["site_id"] != "-1":
        parts.append(f"at {site}")
    return " ".join(parts)


def _describe_created_site(ev: dict, p: LegendsParser) -> str:
    entity = _entity_label(ev.get("civ_id"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"Entity {entity} founded site {site}"


def _describe_masterpiece_item(ev: dict, p: LegendsParser) -> str:
    maker = _hf_label(ev.get("hfid"), p)
    skill = ev.get("skill_at_time", "?")
    site = _site_label(ev.get("site_id"), p)
    parts = [f"{maker} created a masterpiece (skill: {skill})"]
    if ev.get("site_id") and ev["site_id"] != "-1":
        parts.append(f"at {site}")
    return " ".join(parts)


def _describe_hf_simple_battle(ev: dict, p: LegendsParser) -> str:
    group1 = _hf_label(ev.get("group_1_hfid"), p)
    group2 = _hf_label(ev.get("group_2_hfid"), p)
    return f"{group1} fought {group2}"


def _describe_add_hf_entity_link(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("hfid"), p)
    entity = _entity_label(ev.get("civ_id"), p)
    link = ev.get("link_type", ev.get("link", "member"))
    return f"{hf} joined entity {entity} (link: {link})"


def _describe_add_hf_hf_link(ev: dict, p: LegendsParser) -> str:
    hf1 = _hf_label(ev.get("hfid"), p)
    hf2 = _hf_label(ev.get("hfid_target"), p)
    link = ev.get("link_type", "?")
    return f"{hf1} formed {link} relationship with {hf2}"


def _describe_add_hf_site_link(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("hfid") or ev.get("histfig_id"), p)
    site = _site_label(ev.get("site_id"), p)
    link = ev.get("link_type", "?")
    return f"{hf} linked to site {site} ({link})"


def _describe_remove_hf_entity_link(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("hfid"), p)
    entity = _entity_label(ev.get("civ_id"), p)
    link = ev.get("link_type", ev.get("link", "member"))
    return f"{hf} left entity {entity} (link: {link})"


def _describe_remove_hf_hf_link(ev: dict, p: LegendsParser) -> str:
    hf1 = _hf_label(ev.get("hfid"), p)
    hf2 = _hf_label(ev.get("hfid_target"), p)
    link = ev.get("link_type", "?")
    return f"{hf1} ended {link} relationship with {hf2}"


def _describe_change_hf_job(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    new_job = ev.get("new_job", "?")
    old_job = ev.get("old_job", "?")
    return f"{hf} changed job from {old_job} to {new_job} at {site}"


def _describe_hf_travel(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("group_hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    return_ = ev.get("return", "false")
    if return_ == "true":
        return f"{hf} returned to {site}"
    return f"{hf} traveled to {site}"


def _describe_hf_new_pet(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("group_hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{hf} gained a new pet at {site}"


def _describe_creature_devoured(ev: dict, p: LegendsParser) -> str:
    eater = _hf_label(ev.get("eater_hfid"), p)
    victim = _hf_label(ev.get("victim_hfid") or ev.get("hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{eater} devoured {victim} at {site}"


def _describe_hf_wounded(ev: dict, p: LegendsParser) -> str:
    woundee = _hf_label(ev.get("woundee_hfid"), p)
    wounder = _hf_label(ev.get("wounder_hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{woundee} was wounded by {wounder} at {site}"


def _describe_attacked_site(ev: dict, p: LegendsParser) -> str:
    attacker = _entity_label(ev.get("attacker_civ_id"), p)
    defender = _entity_label(ev.get("defender_civ_id"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{attacker} attacked {site} (defended by {defender})"


def _describe_destroyed_site(ev: dict, p: LegendsParser) -> str:
    attacker = _entity_label(ev.get("attacker_civ_id"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{attacker} destroyed {site}"


def _describe_plundered_site(ev: dict, p: LegendsParser) -> str:
    attacker = _entity_label(ev.get("attacker_civ_id"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{attacker} plundered {site}"


def _describe_field_battle(ev: dict, p: LegendsParser) -> str:
    attacker = _entity_label(ev.get("attacker_civ_id"), p)
    defender = _entity_label(ev.get("defender_civ_id"), p)
    return f"Field battle: {attacker} vs {defender}"


def _describe_written_content_composed(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("hfid") or ev.get("hist_figure_id"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{hf} composed a written work at {site}"


def _describe_entity_created(ev: dict, p: LegendsParser) -> str:
    entity = _entity_label(ev.get("entity_id"), p)
    site = _site_label(ev.get("site_id"), p)
    parts = [f"Entity {entity} was created"]
    if ev.get("site_id") and ev["site_id"] != "-1":
        parts.append(f"at {site}")
    return " ".join(parts)


def _describe_reclaim_site(ev: dict, p: LegendsParser) -> str:
    entity = _entity_label(ev.get("civ_id"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"Entity {entity} reclaimed {site}"


def _describe_new_site_leader(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{hf} became the new leader of {site}"


def _describe_hf_abducted(ev: dict, p: LegendsParser) -> str:
    target = _hf_label(ev.get("target_hfid"), p)
    snatcher = _hf_label(ev.get("snatcher_hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{target} was abducted by {snatcher} from {site}"


def _describe_hf_revived(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{hf} was revived at {site}"


def _describe_item_stolen(ev: dict, p: LegendsParser) -> str:
    thief = _hf_label(ev.get("histfig_id") or ev.get("hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{thief} stole an item from {site}"


def _describe_hf_attacked_site(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("attacker_hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{hf} attacked {site}"


def _describe_hf_destroyed_site(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("attacker_hfid"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{hf} destroyed {site}"


def _describe_peace_accepted(ev: dict, p: LegendsParser) -> str:
    src = _entity_label(ev.get("source") or ev.get("entity_id_1"), p)
    dst = _entity_label(ev.get("destination") or ev.get("entity_id_2"), p)
    return f"Peace accepted between {src} and {dst}"


def _describe_peace_rejected(ev: dict, p: LegendsParser) -> str:
    src = _entity_label(ev.get("source") or ev.get("entity_id_1"), p)
    dst = _entity_label(ev.get("destination") or ev.get("entity_id_2"), p)
    return f"Peace rejected between {src} and {dst}"


def _describe_site_taken_over(ev: dict, p: LegendsParser) -> str:
    attacker = _entity_label(ev.get("attacker_civ_id") or ev.get("new_site_civ_id"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"{attacker} took over {site}"


def _describe_artifact_possessed(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("hfid") or ev.get("hist_figure_id"), p)
    artifact = _artifact_label(ev.get("artifact_id"), p)
    return f"{hf} came to possess artifact {artifact}"


def _describe_artifact_stored(ev: dict, p: LegendsParser) -> str:
    artifact = _artifact_label(ev.get("artifact_id"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"Artifact {artifact} was stored at {site}"


def _describe_artifact_lost(ev: dict, p: LegendsParser) -> str:
    artifact = _artifact_label(ev.get("artifact_id"), p)
    site = _site_label(ev.get("site_id"), p)
    return f"Artifact {artifact} was lost at {site}"


def _describe_knowledge_discovered(ev: dict, p: LegendsParser) -> str:
    hf = _hf_label(ev.get("hfid"), p)
    knowledge = ev.get("knowledge", "?")
    return f"{hf} discovered {knowledge}"


_DESCRIBERS: dict[str, Any] = {
    "hf died": _describe_hf_died,
    "artifact created": _describe_artifact_created,
    "change hf state": _describe_change_hf_state,
    "created site": _describe_created_site,
    "masterpiece item": _describe_masterpiece_item,
    "hf simple battle event": _describe_hf_simple_battle,
    "add hf entity link": _describe_add_hf_entity_link,
    "add hf hf link": _describe_add_hf_hf_link,
    "add hf site link": _describe_add_hf_site_link,
    "remove hf entity link": _describe_remove_hf_entity_link,
    "remove hf hf link": _describe_remove_hf_hf_link,
    "change hf job": _describe_change_hf_job,
    "hf travel": _describe_hf_travel,
    "hf new pet": _describe_hf_new_pet,
    "creature devoured": _describe_creature_devoured,
    "hf wounded": _describe_hf_wounded,
    "attacked site": _describe_attacked_site,
    "destroyed site": _describe_destroyed_site,
    "plundered site": _describe_plundered_site,
    "field battle": _describe_field_battle,
    "written content composed": _describe_written_content_composed,
    "entity created": _describe_entity_created,
    "reclaim site": _describe_reclaim_site,
    "new site leader": _describe_new_site_leader,
    "hf abducted": _describe_hf_abducted,
    "hf revived": _describe_hf_revived,
    "item stolen": _describe_item_stolen,
    "hf attacked site": _describe_hf_attacked_site,
    "hf destroyed site": _describe_hf_destroyed_site,
    "peace accepted": _describe_peace_accepted,
    "peace rejected": _describe_peace_rejected,
    "site taken over": _describe_site_taken_over,
    "artifact possessed": _describe_artifact_possessed,
    "artifact stored": _describe_artifact_stored,
    "artifact lost": _describe_artifact_lost,
    "knowledge discovered": _describe_knowledge_discovered,
}


def describe_event(event: dict, parser: LegendsParser) -> str:
    """Return a human-readable one-line description of *event*.

    Uses a specific describer for common event types; falls back to
    raw key=value pairs for unknown types.
    """
    etype = event.get("type", "?")
    describer = _DESCRIBERS.get(etype)
    if describer:
        return describer(event, parser)

    # Fallback: show interesting key=value pairs
    skip = {"id", "type", "year", "seconds72"}
    parts: list[str] = []
    for k, v in event.items():
        if k in skip or v in ("", "-1", None):
            continue
        parts.append(f"{k}={v}")
    return ", ".join(parts) if parts else "(no details)"


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _resolve_event_fields(ev: dict, parser: LegendsParser) -> list[str]:
    """Resolve ID fields in *ev* to human-readable detail lines."""
    lines: list[str] = []
    # HF fields
    hf_labels = {
        "hfid": "Figure", "hfid1": "Figure 1", "hfid2": "Figure 2",
        "slayer_hfid": "Slayer", "group_hfid": "Group",
        "attacker_hfid": "Attacker", "defender_hfid": "Defender",
        "target_hfid": "Target", "snatcher_hfid": "Snatcher",
        "woundee_hfid": "Woundee", "wounder_hfid": "Wounder",
        "histfig_id": "Figure", "hist_figure_id": "Figure",
        "group_1_hfid": "Group 1", "group_2_hfid": "Group 2",
        "eater_hfid": "Eater", "victim_hfid": "Victim",
        "changee_hfid": "Changee", "changer_hfid": "Changer",
        "doer_hfid": "Doer", "holder_hfid": "Holder",
        "builder_hfid": "Builder", "maker_hfid": "Maker",
        "hfid_target": "Target",
    }
    for field, label in hf_labels.items():
        val = ev.get(field)
        if val and val != "-1":
            lines.append(f"  {label}: {_hf_label(val, parser)}")

    # Entity fields
    entity_labels = {
        "civ_id": "Civ", "entity_id": "Entity",
        "attacker_civ_id": "Attacker Civ", "defender_civ_id": "Defender Civ",
        "site_civ_id": "Site Civ", "new_site_civ_id": "New Site Civ",
        "target_entity_id": "Target Entity",
    }
    for field, label in entity_labels.items():
        val = ev.get(field)
        if val and val != "-1":
            lines.append(f"  {label}: {_entity_label(val, parser)}")

    # Site fields
    site_labels = {
        "site_id": "Site", "site_id1": "Site 1", "site_id2": "Site 2",
    }
    for field, label in site_labels.items():
        val = ev.get(field)
        if val and val != "-1":
            lines.append(f"  {label}: {_site_label(val, parser)}")

    # Artifact fields
    art_val = ev.get("artifact_id")
    if art_val and art_val != "-1":
        lines.append(f"  Artifact: {_artifact_label(art_val, parser)}")

    # Cause / skill / misc scalar fields of interest
    for field, label in [("cause", "Cause"), ("skill_at_time", "Skill"),
                         ("link_type", "Link Type"), ("state", "State"),
                         ("knowledge", "Knowledge"), ("new_job", "New Job"),
                         ("old_job", "Old Job")]:
        val = ev.get(field)
        if val and val != "-1":
            lines.append(f"  {label}: {val}")

    return lines


def print_event(ev: dict, parser: LegendsParser, *, raw: bool = False) -> None:
    """Print a single event in human-readable form."""
    year = format_year(ev.get("year"))
    seconds = ev.get("seconds72", "?")
    eid = ev.get("id", "?")
    etype = ev.get("type", "?")
    header = f"Year {year}, s72 {seconds} #{eid}: {etype}"
    print(header)

    if raw:
        for k, v in ev.items():
            if k not in ("id", "year", "seconds72", "type"):
                print(f"  {k}: {v}")
    else:
        desc = describe_event(ev, parser)
        print(f"  {desc}")
        for line in _resolve_event_fields(ev, parser):
            print(line)
    print()


def print_summary(events: list[dict]) -> None:
    """Print a count-by-type summary table."""
    counts: Counter[str] = Counter()
    for ev in events:
        counts[ev.get("type", "?")] += 1

    if not counts:
        print("No events found.")
        return

    # Column widths
    max_type_len = max(len(t) for t in counts)
    max_count_len = max(len(str(c)) for c in counts.values())

    print(f"{'Event Type':<{max_type_len}}  {'Count':>{max_count_len}}")
    print(f"{'-' * max_type_len}  {'-' * max_count_len}")
    for etype, count in counts.most_common():
        print(f"{etype:<{max_type_len}}  {count:>{max_count_len}}")
    print(f"\nTotal: {sum(counts.values())} events across {len(counts)} types")


def print_types(parser: LegendsParser) -> None:
    """Print an alphabetical list of all event types in the data."""
    types: set[str] = set()
    for ev in parser.events:
        t = ev.get("type")
        if t:
            types.add(t)

    if not types:
        print("No events found.")
        return

    print(f"Event types ({len(types)} total):\n")
    for t in sorted(types):
        print(f"  {t}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    ap = argparse.ArgumentParser(
        description="Browse and filter Dwarf Fortress Legends XML events.",
    )
    add_common_args(ap)

    ap.add_argument(
        "--type", dest="event_type", type=str, default=None,
        help="Filter by event type (partial match allowed).",
    )
    ap.add_argument(
        "--site", type=str, default=None,
        help="Filter by site name or ID.",
    )
    ap.add_argument(
        "--entity", type=str, default=None,
        help="Filter by entity name or ID.",
    )
    ap.add_argument(
        "--figure", type=str, default=None,
        help="Filter by historical figure name or ID.",
    )
    ap.add_argument(
        "--limit", type=int, default=100,
        help="Max events to show (default: 100).",
    )
    ap.add_argument(
        "--summary", action="store_true", default=False,
        help="Show count-by-type summary instead of listing events.",
    )
    ap.add_argument(
        "--types", action="store_true", default=False,
        help="List all available event types and exit.",
    )
    ap.add_argument(
        "--raw", action="store_true", default=False,
        help="Show raw event dict (useful for debugging).",
    )
    return ap


def _resolve_event_type(requested: str, parser: LegendsParser) -> str | None:
    """Resolve a (possibly partial) event type to an exact match.

    Returns the exact type string, or None if no match.  If the exact
    string is present, prefer it over partial matches.
    """
    all_types: set[str] = {ev.get("type", "") for ev in parser.events}

    # Exact match first
    if requested in all_types:
        return requested

    # Partial (substring) match
    needle = requested.lower()
    matches = [t for t in all_types if needle in t.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"Ambiguous type '{requested}'. Matches:", file=sys.stderr)
        for m in sorted(matches):
            print(f"  {m}", file=sys.stderr)
        sys.exit(1)

    print(f"No event type matching '{requested}' found.", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    """Entry point."""
    configure_output()
    ap = build_parser()
    args = ap.parse_args()

    # --types mode: only needs parser for event list
    if args.types:
        with get_parser_from_args(args) as parser:
            print_types(parser)
        return

    # Validate that at least one filter is specified (unless --types)
    has_filter = any([
        args.event_type,
        args.site,
        args.entity,
        args.figure,
        args.year,
        args.year_from,
        args.year_to,
    ])
    if not has_filter:
        ap.error(
            "At least one filter is required: --type, --site, --entity, "
            "--figure, --year, --year-from, or --year-to."
        )

    # Normalise year args
    year_from: int | None = args.year if args.year else args.year_from
    year_to: int | None = args.year if args.year else args.year_to

    with get_parser_from_args(args) as parser:
        # Resolve human-friendly names to IDs
        site_id: str | None = None
        entity_id: str | None = None
        hf_id: str | None = None
        event_type: str | None = None

        if args.site:
            site_id = parser.resolve_site_id(args.site)
        if args.entity:
            entity_id = parser.resolve_entity_id(args.entity)
        if args.figure:
            hf_id = parser.resolve_hf_id(args.figure)
        if args.event_type:
            event_type = _resolve_event_type(args.event_type, parser)

        # Filter
        events = parser.filter_events(
            year_from=year_from,
            year_to=year_to,
            event_type=event_type,
            site_id=site_id,
            entity_id=entity_id,
            hf_id=hf_id,
        )

        # Output
        if args.json:
            print_json(events[:args.limit] if not args.summary else events)
            return

        if args.summary:
            print_summary(events)
            return

        if not events:
            print("No events matched the given filters.")
            return

        total = len(events)
        shown = min(total, args.limit)
        print(f"Showing {shown} of {total} matching events:\n")
        for ev in events[:args.limit]:
            print_event(ev, parser, raw=args.raw)


if __name__ == "__main__":
    main()
