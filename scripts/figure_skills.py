#!/usr/bin/env python3
"""Show detailed skill information for a historical figure from the Legends XML.

Usage:
    python scripts/figure_skills.py "atir"
    python scripts/figure_skills.py "atir" --sort name
    python scripts/figure_skills.py "atir" --min-level Skilled
    python scripts/figure_skills.py "atir" --compare "solon"
    python scripts/figure_skills.py "atir" --json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup so ``python scripts/figure_skills.py`` works from the DF root.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.legends_parser import (
    LegendsParser,
    add_common_args,
    configure_output,
    format_hf_summary,
    get_parser_from_args,
    print_json,
    skill_level_name,
)

# ---------------------------------------------------------------------------
# Skill category mapping
# ---------------------------------------------------------------------------

COMBAT_SKILLS: frozenset[str] = frozenset({
    "MELEE_COMBAT", "RANGED_COMBAT", "WRESTLING", "STRIKING", "KICKING",
    "BITING", "DODGING", "SHIELD", "ARMOR", "HAMMER", "SWORD", "SPEAR",
    "AXE", "MACE", "CROSSBOW", "BOW", "PIKE", "WHIP", "DAGGER", "KNIFE",
    "BLOWGUN",
})

MILITARY_SKILLS: frozenset[str] = frozenset({
    "MILITARY_TACTICS", "LEADERSHIP", "TEACHING", "DISCIPLINE",
    "CONCENTRATION", "SITUATIONAL_AWARENESS", "STANCE_STRIKE",
    "GRASP_STRIKE", "BITE",
})

SOCIAL_SKILLS: frozenset[str] = frozenset({
    "PERSUASION", "NEGOTIATION", "JUDGING_INTENT", "LYING", "INTIMIDATION",
    "CONVERSATION", "COMEDY", "FLATTERY", "CONSOLING", "PACIFY",
})

_LEVEL_ORDER: list[str] = [
    "Dabbling", "Novice", "Adequate", "Competent", "Skilled", "Proficient",
    "Talented", "Adept", "Expert", "Professional", "Accomplished", "Great",
    "Master", "High Master", "Grand Master", "Legendary",
]


def _level_rank(level_name: str) -> int:
    """Return a sort-key integer for a skill level name (higher is better)."""
    base = level_name.replace("Legendary+", "Legendary_plus_")
    if base.startswith("Legendary_plus_"):
        bonus = base.replace("Legendary_plus_", "")
        return len(_LEVEL_ORDER) + int(bonus) if bonus else len(_LEVEL_ORDER) - 1
    try:
        return _LEVEL_ORDER.index(level_name)
    except ValueError:
        return -1


def categorize_skill(skill_name: str) -> str:
    """Return the category string for a given skill name."""
    if skill_name in COMBAT_SKILLS:
        return "Combat"
    if skill_name in MILITARY_SKILLS:
        return "Military"
    if skill_name in SOCIAL_SKILLS:
        return "Social"
    return "Craft/Labor"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _parse_skills(hf: dict) -> list[dict[str, Any]]:
    """Parse the hf_skills list into enriched dicts."""
    raw: list[dict[str, str]] = hf.get("hf_skills", [])
    results: list[dict[str, Any]] = []
    for entry in raw:
        ip = int(entry.get("total_ip", "0"))
        name = entry.get("skill", "UNKNOWN")
        level = skill_level_name(ip)
        results.append({
            "skill": name,
            "total_ip": ip,
            "level": level,
            "level_rank": _level_rank(level),
            "category": categorize_skill(name),
        })
    return results


def _apply_min_level(skills: list[dict[str, Any]], min_level: str) -> list[dict[str, Any]]:
    """Filter skills to those at or above *min_level*."""
    threshold = _level_rank(min_level)
    return [s for s in skills if s["level_rank"] >= threshold]


def _sort_skills(
    skills: list[dict[str, Any]], sort_key: str,
) -> list[dict[str, Any]]:
    """Sort skills by the requested key."""
    if sort_key == "name":
        return sorted(skills, key=lambda s: s["skill"])
    if sort_key == "ip":
        return sorted(skills, key=lambda s: s["total_ip"], reverse=True)
    # Default: level (descending IP breaks ties)
    return sorted(skills, key=lambda s: (s["level_rank"], s["total_ip"]), reverse=True)


def _get_masterpiece_events(
    parser: LegendsParser, hf_id: str,
) -> list[dict[str, Any]]:
    """Return masterpiece-item events where *hf_id* is the maker."""
    events = parser.filter_events(event_type="masterpiece item")
    return [e for e in events if e.get("maker_hfid") == hf_id or e.get("hfid") == hf_id]


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

_COL_SKILL = 24
_COL_LEVEL = 16
_COL_IP = 10
_LINE_WIDTH = _COL_SKILL + _COL_LEVEL + _COL_IP


def _print_skills_table(skills: list[dict[str, Any]]) -> None:
    """Print a formatted skills table."""
    header = (
        f"{'SKILL NAME':<{_COL_SKILL}}"
        f"{'Level':<{_COL_LEVEL}}"
        f"{'IP':>{_COL_IP}}"
    )
    print(header)
    print("\u2500" * _LINE_WIDTH)
    for s in skills:
        print(
            f"{s['skill']:<{_COL_SKILL}}"
            f"{s['level']:<{_COL_LEVEL}}"
            f"{s['total_ip']:>{_COL_IP},}"
        )


def _print_categories(skills: list[dict[str, Any]]) -> None:
    """Print skills grouped by category."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for s in skills:
        groups.setdefault(s["category"], []).append(s)

    order = ["Combat", "Military", "Social", "Craft/Labor"]
    for cat in order:
        group = groups.get(cat)
        if not group:
            continue
        group_sorted = sorted(group, key=lambda s: s["total_ip"], reverse=True)
        names = ", ".join(
            f"{s['skill']} ({s['level']})" for s in group_sorted
        )
        print(f"  {cat}: {names}")


def _print_masterpieces(
    events: list[dict[str, Any]], parser: LegendsParser,
) -> None:
    """Print masterpiece creation events."""
    if not events:
        return
    print(f"\nMasterpiece Events ({len(events)}):")
    print("\u2500" * _LINE_WIDTH)
    for ev in events:
        year = ev.get("year", "?")
        item_type = ev.get("item_type", ev.get("item_subtype", "item"))
        mat = ev.get("mat", "")
        site_id = ev.get("site_id", "")
        site_name = parser.get_site_name(site_id) if site_id else "unknown site"
        desc = f"{mat} {item_type}".strip() if mat else item_type
        print(f"  Year {year}: created a masterwork {desc} at {site_name}")


def _print_comparison(
    name_a: str,
    skills_a: list[dict[str, Any]],
    name_b: str,
    skills_b: list[dict[str, Any]],
) -> None:
    """Print a side-by-side comparison of two figures' skills."""
    map_a = {s["skill"]: s for s in skills_a}
    map_b = {s["skill"]: s for s in skills_b}
    all_skills = sorted(set(map_a) | set(map_b))

    col_s = 24
    col_v = 22

    header = (
        f"{'SKILL':<{col_s}}"
        f"{name_a:<{col_v}}"
        f"{name_b:<{col_v}}"
    )
    print(f"\nComparison: {name_a} vs {name_b}")
    print(header)
    print("\u2500" * (col_s + col_v * 2))
    for sk in all_skills:
        a = map_a.get(sk)
        b = map_b.get(sk)
        a_str = f"{a['level']} ({a['total_ip']:,})" if a else "\u2014"
        b_str = f"{b['level']} ({b['total_ip']:,})" if b else "\u2014"
        print(f"{sk:<{col_s}}{a_str:<{col_v}}{b_str:<{col_v}}")


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def _build_json(
    hf: dict,
    summary: str,
    skills: list[dict[str, Any]],
    masterpieces: list[dict[str, Any]],
    compare_hf: dict | None,
    compare_summary: str | None,
    compare_skills: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Build a JSON-serialisable dict for the full output."""
    skill_dicts = [
        {"skill": s["skill"], "level": s["level"], "total_ip": s["total_ip"],
         "category": s["category"]}
        for s in skills
    ]
    data: dict[str, Any] = {
        "subject": summary,
        "hf_id": hf.get("id"),
        "skills": skill_dicts,
        "masterpiece_events": [
            {"year": e.get("year"), "item_type": e.get("item_type", e.get("item_subtype")),
             "mat": e.get("mat", ""), "site_id": e.get("site_id")}
            for e in masterpieces
        ],
    }
    if compare_hf and compare_skills is not None:
        data["comparison"] = {
            "subject": compare_summary,
            "hf_id": compare_hf.get("id"),
            "skills": [
                {"skill": s["skill"], "level": s["level"], "total_ip": s["total_ip"],
                 "category": s["category"]}
                for s in compare_skills
            ],
        }
    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    p = argparse.ArgumentParser(
        description="Show detailed skill information for a historical figure.",
    )
    p.add_argument("name", help="Historical figure name or numeric ID.")
    p.add_argument(
        "--sort", choices=["level", "name", "ip"], default="level",
        help="Sort order for the skills table (default: level/IP descending).",
    )
    p.add_argument(
        "--min-level", default=None, metavar="LEVEL",
        help="Only show skills at or above this level (e.g. 'Skilled').",
    )
    p.add_argument(
        "--compare", default=None, metavar="NAME2",
        help="Compare skills side-by-side with another figure.",
    )
    add_common_args(p)
    return p


def main() -> None:
    """Entry point."""
    configure_output()
    args = build_parser().parse_args()

    with get_parser_from_args(args) as parser:
        # Resolve primary figure
        hf_id = parser.resolve_hf_id(args.name)
        hf = parser.hf_map[hf_id]
        summary = format_hf_summary(hf, parser)

        # Parse & filter skills
        skills = _parse_skills(hf)
        if args.min_level:
            skills = _apply_min_level(skills, args.min_level)
        skills = _sort_skills(skills, args.sort)

        # Masterpiece events
        masterpieces = _get_masterpiece_events(parser, hf_id)

        # Optional comparison figure
        compare_hf: dict | None = None
        compare_summary: str | None = None
        compare_skills: list[dict[str, Any]] | None = None
        if args.compare:
            cmp_id = parser.resolve_hf_id(args.compare)
            compare_hf = parser.hf_map[cmp_id]
            compare_summary = format_hf_summary(compare_hf, parser)
            compare_skills = _parse_skills(compare_hf)
            if args.min_level:
                compare_skills = _apply_min_level(compare_skills, args.min_level)
            compare_skills = _sort_skills(compare_skills, args.sort)

        # Output
        if args.json:
            print_json(_build_json(
                hf, summary, skills, masterpieces,
                compare_hf, compare_summary, compare_skills,
            ))
            return

        # Human-readable output
        print(f"Subject: {summary}")
        print()

        if skills:
            _print_skills_table(skills)
        else:
            print("  (no skills recorded)")

        _print_masterpieces(masterpieces, parser)

        if skills:
            print(f"\nSkill Categories:")
            _print_categories(skills)

        if compare_hf and compare_skills is not None:
            short_a = hf.get("name", args.name)
            short_b = compare_hf.get("name", args.compare)
            _print_comparison(short_a, skills, short_b, compare_skills)


if __name__ == "__main__":
    main()
