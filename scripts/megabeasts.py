"""
megabeasts.py — List megabeasts, forgotten beasts, titans, and demons.

Shows kill counts, status, locations, and notable victims for every
non-standard-race historical figure (dragons, giants, demons, etc.)
or any figure tagged as a deity.

Usage:
    python scripts/megabeasts.py
    python scripts/megabeasts.py --alive-only
    python scripts/megabeasts.py --min-kills 5 --json
    python scripts/megabeasts.py --race DRAGON --dead-only
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.legends_parser import (
    LegendsParser,
    add_common_args,
    configure_output,
    format_year,
    get_parser_from_args,
    print_json,
)

# Races considered "common" — everything else is a potential megabeast/titan/FB.
COMMON_RACES: set[str] = {
    "DWARF",
    "ELF",
    "GOBLIN",
    "HUMAN",
    "KOBOLD",
}


# ------------------------------------------------------------------
# Data extraction
# ------------------------------------------------------------------


def _build_kill_index(parser: LegendsParser) -> dict[str, list[dict[str, Any]]]:
    """Map slayer HF-ID → list of kill records from ``hf died`` events."""
    kills: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ev in parser.events:
        if ev.get("type") != "hf died":
            continue
        slayer = str(ev.get("slayer_hfid", ""))
        if slayer in ("", "-1"):
            continue
        victim_id = str(ev.get("hfid") or ev.get("hfid2") or "")
        victim_hf = parser.hf_map.get(victim_id)
        kills[slayer].append({
            "year": ev.get("year", "?"),
            "victim_id": victim_id,
            "victim_name": (
                (victim_hf.get("name") or "unnamed").title()
                if victim_hf
                else f"Unknown ({victim_id})"
            ),
            "victim_race": (
                (victim_hf.get("race") or "?").replace("_", " ").title()
                if victim_hf
                else "?"
            ),
            "cause": ev.get("death_cause") or ev.get("cause") or "?",
            "site_id": ev.get("site_id"),
        })
    return kills


def _find_slayer(hf_id: str, parser: LegendsParser) -> dict[str, Any] | None:
    """Return info about who killed *hf_id*, or ``None``."""
    for ev in parser.events:
        if ev.get("type") != "hf died":
            continue
        victim_id = str(ev.get("hfid") or ev.get("hfid2") or "")
        if victim_id != hf_id:
            continue
        slayer_id = str(ev.get("slayer_hfid", ""))
        if slayer_id in ("", "-1"):
            return {"year": ev.get("year", "?"), "cause": ev.get("cause") or "?"}
        slayer_hf = parser.hf_map.get(slayer_id)
        return {
            "slayer_id": slayer_id,
            "slayer_name": (
                (slayer_hf.get("name") or "unnamed").title()
                if slayer_hf
                else f"Unknown ({slayer_id})"
            ),
            "slayer_race": (
                (slayer_hf.get("race") or "?").replace("_", " ").title()
                if slayer_hf
                else "?"
            ),
            "year": ev.get("year", "?"),
            "cause": ev.get("death_cause") or ev.get("cause") or "?",
        }
    return None


def _last_known_site(hf_id: str, parser: LegendsParser) -> str | None:
    """Return the site-ID from the most recent event involving *hf_id*."""
    last_site: str | None = None
    for ev in parser.events:
        sid = ev.get("site_id")
        if not sid or str(sid) == "-1":
            continue
        # Check if this figure is mentioned in the event
        for key in ("hfid", "hfid1", "hfid2", "slayer_hfid",
                     "group_1_hfid", "group_2_hfid"):
            if str(ev.get(key, "")) == hf_id:
                last_site = str(sid)
                break
    return last_site


def _is_megabeast(hf: dict[str, Any]) -> bool:
    """Return ``True`` if the HF qualifies as a megabeast/titan/FB/demon."""
    race = (hf.get("race") or "").upper()
    if race and race not in COMMON_RACES:
        return True
    # The parser stores <deity/> as True, absence as False.
    if hf.get("deity"):
        return True
    return False


def collect_megabeasts(
    parser: LegendsParser,
    *,
    alive_only: bool = False,
    dead_only: bool = False,
    min_kills: int = 0,
    race_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Return a list of megabeast dicts, sorted by kill count descending."""
    kill_index = _build_kill_index(parser)
    results: list[dict[str, Any]] = []

    for hf in parser.hf_map.values():
        if not _is_megabeast(hf):
            continue

        hf_id = str(hf["id"])
        race = (hf.get("race") or "UNKNOWN").upper()
        death_year = hf.get("death_year")
        is_alive = str(death_year) == "-1"

        # Filters
        if alive_only and not is_alive:
            continue
        if dead_only and is_alive:
            continue
        if race_filter and race != race_filter.upper():
            continue

        kills = kill_index.get(hf_id, [])
        if len(kills) < min_kills:
            continue

        name = (hf.get("name") or "Unnamed").title()
        caste = (hf.get("caste") or "").upper()
        birth_year = hf.get("birth_year")

        # Spheres — parser stores as "sphere" (singular), may be str or list
        spheres_raw = hf.get("sphere") or hf.get("spheres") or []
        if isinstance(spheres_raw, str):
            spheres_raw = [spheres_raw]

        # Who killed them / cause of death
        slayer_info = None if is_alive else _find_slayer(hf_id, parser)

        # Last known location (only meaningful if alive)
        location_site_id = _last_known_site(hf_id, parser) if is_alive else None
        location_name = (
            parser.get_site_name(location_site_id)
            if location_site_id
            else None
        )

        entry: dict[str, Any] = {
            "id": hf_id,
            "name": name,
            "race": race.replace("_", " ").title(),
            "caste": caste.replace("_", " ").title() if caste else "",
            "alive": is_alive,
            "birth_year": format_year(birth_year),
            "death_year": format_year(death_year) if not is_alive else None,
            "deity": hf.get("deity") is not None,
            "spheres": spheres_raw,
            "kill_count": len(kills),
            "kills": kills,
            "slayer": slayer_info,
            "location": location_name,
            "location_site_id": location_site_id,
        }
        results.append(entry)

    results.sort(key=lambda e: e["kill_count"], reverse=True)
    return results


# ------------------------------------------------------------------
# Display helpers
# ------------------------------------------------------------------


def _print_entry(entry: dict[str, Any]) -> None:
    """Print a single megabeast entry in human-readable format."""
    header = entry["name"]
    race_str = entry["race"]
    if entry["caste"]:
        header += f" ({race_str}, {entry['caste'].lower()})"
    else:
        header += f" ({race_str})"
    print(f"\n{header}")

    # Status
    if entry["alive"]:
        status = "Alive"
        if entry["location"]:
            status += f" (last seen at {entry['location']})"
    else:
        death_yr = entry["death_year"] or "?"
        slayer = entry.get("slayer")
        if slayer and slayer.get("slayer_name"):
            status = (
                f"Dead (year {death_yr}, killed by "
                f"{slayer['slayer_name']} [{slayer.get('slayer_race', '?')}])"
            )
        elif slayer and slayer.get("cause"):
            status = f"Dead (year {death_yr}, cause: {slayer['cause']})"
        else:
            status = f"Dead (year {death_yr})"
    print(f"  Status: {status}")

    # Kills
    kc = entry["kill_count"]
    print(f"  Kills: {kc} known")
    if kc > 0:
        for k in entry["kills"][:10]:
            site_str = ""
            if k.get("site_id"):
                site_str = f" (year {k['year']})"
            else:
                site_str = f" (year {k['year']})"
            print(f"    - {k['victim_name']} ({k['victim_race']}){site_str}")
        if kc > 10:
            print(f"    … and {kc - 10} more")

    # Spheres
    if entry["spheres"]:
        print(f"  Spheres: {', '.join(entry['spheres'])}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------


def main() -> None:
    """Entry point for megabeasts CLI."""
    configure_output()

    ap = argparse.ArgumentParser(
        description=(
            "List megabeasts, forgotten beasts, titans, and demons from "
            "the Legends XML, sorted by kill count."
        ),
    )
    add_common_args(ap)
    ap.add_argument(
        "--alive-only",
        action="store_true",
        default=False,
        help="Show only living megabeasts.",
    )
    ap.add_argument(
        "--dead-only",
        action="store_true",
        default=False,
        help="Show only dead megabeasts.",
    )
    ap.add_argument(
        "--min-kills",
        type=int,
        default=0,
        metavar="N",
        help="Only show figures with at least N kills.",
    )
    ap.add_argument(
        "--race",
        type=str,
        default=None,
        metavar="RACE",
        help="Filter by race (e.g. DRAGON, GIANT).",
    )
    args = ap.parse_args()

    with get_parser_from_args(args) as parser:
        entries = collect_megabeasts(
            parser,
            alive_only=args.alive_only,
            dead_only=args.dead_only,
            min_kills=args.min_kills,
            race_filter=args.race,
        )

        if args.json:
            print_json(entries)
            return

        print("\nMegabeasts & Titans")
        print("===================")

        if not entries:
            print("\n  No megabeasts found matching the given filters.")
        else:
            for entry in entries:
                _print_entry(entry)

        print(f"\n--- {len(entries)} megabeast(s) found ---")


if __name__ == "__main__":
    main()
