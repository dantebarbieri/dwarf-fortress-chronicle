"""
dwarf_relations.py — Show relationship details for a historical figure from Legends XML.

Displays family, deity links, social connections, entity memberships,
and relationship events for a given dwarf (or other historical figure).

Usage:
    python scripts/dwarf_relations.py "atir"
    python scripts/dwarf_relations.py 12345 --tree
    python scripts/dwarf_relations.py "sibrek" --all --json
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
    format_hf_summary,
    format_year,
    get_parser_from_args,
    print_json,
)

# HF link types shown by default vs. only with --all
_FAMILY_LINK_TYPES: frozenset[str] = frozenset({
    "spouse", "child", "mother", "father",
})
_DEITY_LINK_TYPES: frozenset[str] = frozenset({"deity"})
_SOCIAL_LINK_TYPES: frozenset[str] = frozenset({
    "master", "apprentice", "companion",
    "former_master", "former_apprentice",
})
_EXTENDED_LINK_TYPES: frozenset[str] = frozenset({
    "prisoner", "imprisoner",
})

# Event types relevant to relationships
_RELATIONSHIP_EVENT_TYPES: frozenset[str] = frozenset({
    "add hf hf link",
    "remove hf hf link",
    "hf relationship denied",
    "hf reunion",
})


# ---------------------------------------------------------------------------
# Data gathering
# ---------------------------------------------------------------------------


def _hf_alive_status(hf: dict) -> str:
    """Return 'alive' or 'dead (year)' for a historical figure."""
    death = hf.get("death_year")
    if death is None or str(death) == "-1":
        return "alive"
    return f"dead (d.{death})"


def _hf_short(hf: dict) -> str:
    """Short display: 'Name (Race, alive/dead)'."""
    name = (hf.get("name") or "Unnamed").title()
    race = (hf.get("race") or "unknown").replace("_", " ").title()
    return f"{name} ({race}, {_hf_alive_status(hf)})"


def _get_linked_hf(parser: LegendsParser, hf_id: str) -> dict | None:
    """Look up an HF by ID, returning None if missing."""
    return parser.hf_map.get(str(hf_id))


def gather_family(
    hf: dict, parser: LegendsParser
) -> dict[str, Any]:
    """Gather family relationships: spouses, children, parents."""
    hf_id = str(hf["id"])
    links = hf.get("hf_links", [])

    spouses: list[dict] = []
    children: list[dict] = []
    father: dict | None = None
    mother: dict | None = None

    for link in links:
        lt = link.get("link_type", "")
        other_id = link.get("hfid")
        if not other_id:
            continue
        other = _get_linked_hf(parser, other_id)
        if not other:
            continue

        if lt == "spouse":
            spouses.append(other)
        elif lt == "child":
            children.append(other)
        elif lt == "father":
            father = other
        elif lt == "mother":
            mother = other

    # Also discover parents by scanning other HFs' child links pointing here
    if father is None or mother is None:
        for candidate in parser.hf_map.values():
            for cl in candidate.get("hf_links", []):
                if cl.get("link_type") == "child" and str(cl.get("hfid")) == hf_id:
                    caste = (candidate.get("caste") or "").lower()
                    if caste == "male" and father is None:
                        father = candidate
                    elif caste == "female" and mother is None:
                        mother = candidate
                    elif father is None:
                        father = candidate
                    elif mother is None:
                        mother = candidate

    return {
        "spouses": spouses,
        "children": children,
        "father": father,
        "mother": mother,
    }


def gather_deity_links(
    hf: dict, parser: LegendsParser
) -> list[dict[str, Any]]:
    """Gather worshipped deities with spheres."""
    result: list[dict[str, Any]] = []
    for link in hf.get("hf_links", []):
        if link.get("link_type") != "deity":
            continue
        deity_id = link.get("hfid")
        if not deity_id:
            continue
        deity = _get_linked_hf(parser, deity_id)
        if not deity:
            continue
        spheres_raw = deity.get("spheres", [])
        if isinstance(spheres_raw, str):
            spheres_raw = [spheres_raw]
        spheres = [s.replace("_", " ").title() for s in spheres_raw]
        result.append({
            "name": (deity.get("name") or "Unknown").title(),
            "id": deity.get("id"),
            "spheres": spheres,
            "link_strength": link.get("link_strength"),
        })
    return result


def gather_social_links(
    hf: dict, parser: LegendsParser, *, include_extended: bool = False
) -> list[dict[str, Any]]:
    """Gather master/apprentice, companion, and optionally prisoner links."""
    allowed = _SOCIAL_LINK_TYPES | (_EXTENDED_LINK_TYPES if include_extended else frozenset())
    result: list[dict[str, Any]] = []
    for link in hf.get("hf_links", []):
        lt = link.get("link_type", "")
        if lt not in allowed:
            continue
        other_id = link.get("hfid")
        if not other_id:
            continue
        other = _get_linked_hf(parser, other_id)
        result.append({
            "link_type": lt.replace("_", " ").title(),
            "name": (other.get("name") or "Unknown").title() if other else f"Unknown ({other_id})",
            "id": other_id,
            "status": _hf_alive_status(other) if other else "unknown",
            "link_strength": link.get("link_strength"),
        })
    return result


def gather_entity_relationships(
    hf: dict, parser: LegendsParser
) -> list[dict[str, Any]]:
    """Gather entity_link entries — which organizations the figure belongs to."""
    result: list[dict[str, Any]] = []
    for link in hf.get("entity_links", []):
        entity_id = link.get("entity_id")
        if not entity_id:
            continue
        ent_name = parser.get_entity_name(entity_id)
        ent = parser.entity_map.get(str(entity_id))
        ent_type = (ent.get("type") or "unknown") if ent else "unknown"
        result.append({
            "entity_id": entity_id,
            "entity_name": ent_name,
            "entity_type": ent_type.replace("_", " ").title(),
            "link_type": (link.get("link_type") or "").replace("_", " ").title(),
            "link_strength": link.get("link_strength"),
        })
    return result


def gather_relationship_events(
    hf: dict, parser: LegendsParser
) -> list[dict[str, Any]]:
    """Gather events of relationship-relevant types involving this figure."""
    hf_id = str(hf["id"])
    results: list[dict[str, Any]] = []
    for ev in parser.get_hf_events(hf_id):
        etype = ev.get("type", "")
        if etype not in _RELATIONSHIP_EVENT_TYPES:
            continue
        # Identify the other party
        other_id = None
        for field in ("hfid1", "hfid2", "hfid"):
            val = ev.get(field)
            if val and str(val) != hf_id:
                other_id = str(val)
                break
        if other_id is None:
            # Both fields might equal hf_id; try all hf fields
            for field in ("hfid1", "hfid2", "hfid"):
                val = ev.get(field)
                if val and str(val) != hf_id:
                    other_id = str(val)
                    break

        other_name = parser.get_hf_name(other_id) if other_id else "Unknown"
        results.append({
            "year": ev.get("year", "?"),
            "type": etype,
            "other_name": other_name,
            "other_id": other_id,
            "link_type": ev.get("link_type", ""),
        })
    return results


# ---------------------------------------------------------------------------
# Family tree rendering
# ---------------------------------------------------------------------------


def render_family_tree(
    hf: dict, family: dict[str, Any], parser: LegendsParser
) -> str:
    """Render a simple text-based family tree up to 2 generations."""
    subject_name = (hf.get("name") or "Unnamed").title()
    father_name = (family["father"].get("name") or "Unknown").title() if family["father"] else "?"
    mother_name = (family["mother"].get("name") or "Unknown").title() if family["mother"] else "?"

    spouse_names = [
        (s.get("name") or "Unknown").title() for s in family["spouses"]
    ]
    spouse_str = " + ".join(spouse_names) if spouse_names else "?"

    child_names = [
        (c.get("name") or "Unknown").title() for c in family["children"]
    ]

    # Grandparents: look up parents of father and mother
    def _get_parents_of(parent_hf: dict | None) -> tuple[str, str]:
        if not parent_hf:
            return ("?", "?")
        pf = gather_family(parent_hf, parser)
        gf = (pf["father"].get("name") or "?").title() if pf["father"] else "?"
        gm = (pf["mother"].get("name") or "?").title() if pf["mother"] else "?"
        return (gf, gm)

    pat_gf, pat_gm = _get_parents_of(family["father"])
    mat_gf, mat_gm = _get_parents_of(family["mother"])

    lines: list[str] = []

    # Grandparent line (only if any known)
    has_grandparents = any(g != "?" for g in (pat_gf, pat_gm, mat_gf, mat_gm))
    if has_grandparents:
        left_gp = f"[{pat_gf}] + [{pat_gm}]" if (pat_gf != "?" or pat_gm != "?") else ""
        right_gp = f"[{mat_gf}] + [{mat_gm}]" if (mat_gf != "?" or mat_gm != "?") else ""
        if left_gp and right_gp:
            lines.append(f"  {left_gp}    {right_gp}")
        elif left_gp:
            lines.append(f"  {left_gp}")
        else:
            lines.append(f"  {right_gp}")
        lines.append("       |" + (" " * 20 + "|" if right_gp and left_gp else ""))

    # Parent line
    lines.append(f"  [{father_name}] + [{mother_name}]")
    lines.append("       |")

    # Subject line
    lines.append(f"  [{subject_name}] + [{spouse_str}]")

    # Children line
    if child_names:
        lines.append("       |")
        lines.append("  " + "  ".join(f"[{c}]" for c in child_names))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def build_json_output(
    hf: dict,
    parser: LegendsParser,
    family: dict[str, Any],
    deities: list[dict[str, Any]],
    social: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    rel_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a JSON-serializable dict of all relationship data."""
    def _hf_json(h: dict | None) -> dict | None:
        if h is None:
            return None
        return {
            "id": h.get("id"),
            "name": (h.get("name") or "Unknown").title(),
            "race": (h.get("race") or "unknown").replace("_", " ").title(),
            "status": _hf_alive_status(h),
        }

    return {
        "subject": {
            "id": hf.get("id"),
            "summary": format_hf_summary(hf, parser),
        },
        "family": {
            "father": _hf_json(family["father"]),
            "mother": _hf_json(family["mother"]),
            "spouses": [_hf_json(s) for s in family["spouses"]],
            "children": [_hf_json(c) for c in family["children"]],
        },
        "deity_links": deities,
        "social_links": social,
        "entity_relationships": entities,
        "relationship_events": rel_events,
    }


def print_human(
    hf: dict,
    parser: LegendsParser,
    family: dict[str, Any],
    deities: list[dict[str, Any]],
    social: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    rel_events: list[dict[str, Any]],
    *,
    show_tree: bool = False,
) -> None:
    """Print human-readable relationship report to stdout."""
    # Subject
    print(f"=== {format_hf_summary(hf, parser)} ===\n")

    # Family
    print("--- Family ---")
    if family["father"]:
        print(f"  Father:  {_hf_short(family['father'])}")
    if family["mother"]:
        print(f"  Mother:  {_hf_short(family['mother'])}")
    if family["spouses"]:
        for sp in family["spouses"]:
            print(f"  Spouse:  {_hf_short(sp)}")
    else:
        print("  Spouse:  (none)")
    if family["children"]:
        for ch in family["children"]:
            print(f"  Child:   {_hf_short(ch)}")
    else:
        print("  Children: (none)")
    if not family["father"] and not family["mother"]:
        print("  Parents: (unknown)")
    print()

    # Family tree
    if show_tree:
        print("--- Family Tree ---")
        print(render_family_tree(hf, family, parser))
        print()

    # Deity links
    if deities:
        print("--- Deity Links ---")
        for d in deities:
            spheres = ", ".join(d["spheres"]) if d["spheres"] else "no spheres"
            strength = f" (strength {d['link_strength']})" if d.get("link_strength") else ""
            print(f"  {d['name']} — {spheres}{strength}")
        print()

    # Social links
    if social:
        print("--- Social Links ---")
        for s in social:
            strength = f" (strength {s['link_strength']})" if s.get("link_strength") else ""
            print(f"  {s['link_type']}: {s['name']} ({s['status']}){strength}")
        print()

    # Entity relationships
    if entities:
        print("--- Entity Relationships ---")
        for e in entities:
            print(f"  {e['link_type']} of {e['entity_name']} ({e['entity_type']})")
        print()

    # Relationship events
    if rel_events:
        print("--- Relationship Events ---")
        for r in rel_events:
            link_info = f" [{r['link_type']}]" if r.get("link_type") else ""
            print(f"  Year {r['year']}: {r['type']}{link_info} — {r['other_name']}")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_argparser() -> argparse.ArgumentParser:
    """Build the argument parser for dwarf_relations."""
    parser = argparse.ArgumentParser(
        description="Show relationship details for a historical figure from Legends XML.",
    )
    parser.add_argument(
        "name",
        type=str,
        help="Historical figure name (partial match) or numeric ID.",
    )
    parser.add_argument(
        "--tree",
        action="store_true",
        default=False,
        help="Show a text-based family tree (up to 2 generations).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        dest="show_all",
        help="Show all relationship types including prisoner/imprisoner links.",
    )
    add_common_args(parser)
    return parser


def main() -> None:
    """Entry point for dwarf_relations CLI."""
    configure_output()
    ap = build_argparser()
    args = ap.parse_args()

    with get_parser_from_args(args) as parser:
        # Resolve figure
        try:
            hf_id = parser.resolve_hf_id(args.name)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        hf = parser.hf_map[hf_id]

        # Gather all relationship data
        family = gather_family(hf, parser)
        deities = gather_deity_links(hf, parser)
        social = gather_social_links(hf, parser, include_extended=args.show_all)
        entities = gather_entity_relationships(hf, parser)
        rel_events = gather_relationship_events(hf, parser)

        if args.json:
            data = build_json_output(hf, parser, family, deities, social, entities, rel_events)
            if args.tree:
                data["family_tree"] = render_family_tree(hf, family, parser)
            print_json(data)
        else:
            print_human(
                hf, parser, family, deities, social, entities, rel_events,
                show_tree=args.tree,
            )


if __name__ == "__main__":
    main()
