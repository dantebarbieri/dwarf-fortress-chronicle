"""
legends_parser.py — Core shared module for parsing Dwarf Fortress Legends XML exports.

Provides the LegendsParser class with lazy-loaded lookup maps for historical figures,
entities, sites, artifacts, events, event collections, and written contents. All parsing
uses iterparse with element clearing to keep memory usage low on large (~63 MB+) exports.

Usage:
    from scripts.legends_parser import LegendsParser, auto_detect_xml

    with LegendsParser("region1-00102-12-13-legends.xml") as lp:
        hf = lp.hf_map["12345"]
        events = lp.get_hf_events("12345", year_from=100, year_to=102)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from functools import cached_property
from pathlib import Path
from typing import Any, Optional
from xml.etree.ElementTree import iterparse


# ---------------------------------------------------------------------------
# DF skill IP thresholds → human-readable names
# ---------------------------------------------------------------------------

_SKILL_THRESHOLDS: list[tuple[int, str]] = [
    (53100, "Legendary"),
    (46100, "Grand Master"),
    (39600, "High Master"),
    (33600, "Master"),
    (28100, "Great"),
    (23100, "Accomplished"),
    (18600, "Professional"),
    (14600, "Expert"),
    (11100, "Adept"),
    (8100, "Talented"),
    (5600, "Proficient"),
    (3600, "Skilled"),
    (2100, "Competent"),
    (1100, "Adequate"),
    (500, "Novice"),
    (0, "Dabbling"),
]

# Fields checked by event_involves_* helpers
_HF_EVENT_FIELDS: frozenset[str] = frozenset({
    "hfid", "hfid1", "hfid2", "slayer_hfid", "group_hfid",
    "attacker_hfid", "defender_hfid", "trickster_hfid", "target_hfid",
    "changee_hfid", "changer_hfid", "doer_hfid", "histfig_id",
    "hist_figure_id", "holder_hfid", "builder_hfid", "maker_hfid",
    "acquirer_hfid", "a_hfid", "d_hfid", "a_leader_hfid",
    "d_leader_hfid", "a_tactician_hfid", "d_tactician_hfid",
    "woundee_hfid", "wounder_hfid", "seeker_hfid", "snatcher_hfid",
    "corruptor_hfid", "identity_hfid", "stash_hfid", "body_hfid",
})

_ENTITY_EVENT_FIELDS: frozenset[str] = frozenset({
    "civ_id", "civ_entity_id", "entity_id", "attacker_civ_id",
    "defender_civ_id", "a_squad_id", "d_squad_id", "site_civ_id",
    "new_site_civ_id", "old_site_civ_id", "attacker_merc_enid",
    "defender_merc_enid", "entity_id_1", "entity_id_2",
    "target_entity_id", "source_entity_id", "join_entity_id",
    "spy_entity_id",
})

_SITE_EVENT_FIELDS: frozenset[str] = frozenset({
    "site_id", "site_id1", "site_id2", "attacker_site_id",
    "defender_site_id", "old_site_id", "new_site_id",
    "source_site_id", "dest_site_id",
})

# Control-character regex (keeps \t, \n, \r)
_CONTROL_CHAR_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f]"
)

# Nested child tags inside <historical_figure> that should be collected as
# lists of dicts rather than scalar values.
_HF_LIST_TAGS: frozenset[str] = frozenset({
    "entity_link", "hf_link", "hf_skill", "entity_position_link",
    "entity_former_position_link", "site_link", "honor_entity",
    "entity_reputation", "entity_squad_link", "entity_former_squad_link",
    "intrigue_actor", "intrigue_plot", "vague_relationship",
    "relationship_profile_hf",
})

# Plural key names for the collected lists (tag → dict key)
_HF_LIST_KEY: dict[str, str] = {
    "entity_link": "entity_links",
    "hf_link": "hf_links",
    "hf_skill": "hf_skills",
    "entity_position_link": "entity_position_links",
    "entity_former_position_link": "entity_former_position_links",
    "site_link": "site_links",
    "honor_entity": "honor_entity",
    "entity_reputation": "entity_reputation",
    "entity_squad_link": "entity_squad_link",
    "entity_former_squad_link": "entity_former_squad_link",
    "intrigue_actor": "intrigue_actor",
    "intrigue_plot": "intrigue_plot",
    "vague_relationship": "vague_relationship",
    "relationship_profile_hf": "relationship_profile_hf",
}

# Simple scalar fields on an HF element (collected directly as key: text)
_HF_SCALAR_FIELDS: frozenset[str] = frozenset({
    "id", "name", "race", "caste", "birth_year", "death_year",
    "birth_seconds72", "death_seconds72", "appeared", "associated_type",
    "deity", "force", "active_interaction", "holds_artifact",
    "current_identity_id", "animated", "animated_string",
    "journey_pet", "ent_pop_id",
})

# Multi-value scalar fields that should always become lists
_HF_MULTI_SCALAR_FIELDS: frozenset[str] = frozenset({
    "spheres", "goals", "interaction_knowledge", "holds_artifact",
    "journey_pet",
})


# =========================================================================
# Module-level utility functions
# =========================================================================


def configure_output() -> None:
    """Reconfigure stdout/stderr for UTF-8 on Windows (cp1252 safe).

    Call this early in each script's ``main()`` to avoid
    ``UnicodeEncodeError`` when printing non-ASCII characters.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def skill_level_name(total_ip: int) -> str:
    """Convert total improvement points to the DF skill level name.

    >>> skill_level_name(0)
    'Dabbling'
    >>> skill_level_name(53100)
    'Legendary'
    >>> skill_level_name(53900)
    'Legendary+2'
    """
    if total_ip >= 53100:
        bonus = (total_ip - 53100) // 400
        return f"Legendary+{bonus}" if bonus > 0 else "Legendary"
    for threshold, name in _SKILL_THRESHOLDS:
        if total_ip >= threshold:
            return name
    return "Dabbling"


def format_year(year_str: str | int | None) -> str:
    """Format a year value for display. Treats -1 as 'present/alive'."""
    if year_str is None:
        return "?"
    yr = str(year_str).strip()
    if yr == "-1" or yr == "":
        return "present"
    return yr


def event_involves_hf(event: dict, hf_id: str) -> bool:
    """Return True if *event* references *hf_id* in any HF-related field."""
    target = str(hf_id)
    for field in _HF_EVENT_FIELDS:
        val = event.get(field)
        if val is None:
            continue
        if isinstance(val, list):
            if target in val:
                return True
        elif str(val) == target:
            return True
    return False


def event_involves_entity(event: dict, entity_id: str) -> bool:
    """Return True if *event* references *entity_id* in any entity field."""
    target = str(entity_id)
    for field in _ENTITY_EVENT_FIELDS:
        val = event.get(field)
        if val is None:
            continue
        if isinstance(val, list):
            if target in val:
                return True
        elif str(val) == target:
            return True
    return False


def event_involves_site(event: dict, site_id: str) -> bool:
    """Return True if *event* references *site_id* in any site field."""
    target = str(site_id)
    for field in _SITE_EVENT_FIELDS:
        val = event.get(field)
        if val is None:
            continue
        if isinstance(val, list):
            if target in val:
                return True
        elif str(val) == target:
            return True
    return False


def auto_detect_xml(directory: str | Path | None = None) -> Path:
    """Find the most recent ``region*.xml`` file in *directory* (default: cwd).

    Raises:
        FileNotFoundError: If no matching file is found.
    """
    search_dir = Path(directory) if directory else Path.cwd()
    candidates = sorted(
        search_dir.glob("region*-legends.xml"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        # Fall back to any region*.xml
        candidates = sorted(
            search_dir.glob("region*.xml"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    if not candidates:
        raise FileNotFoundError(
            f"No region*.xml files found in {search_dir}"
        )
    return candidates[0]


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add standard Legends-related arguments to an argparse parser."""
    parser.add_argument(
        "--xml",
        type=str,
        default=None,
        help="Path to the Legends XML export. Auto-detected if omitted.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Filter to a single year.",
    )
    parser.add_argument(
        "--year-from",
        type=int,
        default=None,
        help="Start year for range filter (inclusive).",
    )
    parser.add_argument(
        "--year-to",
        type=int,
        default=None,
        help="End year for range filter (inclusive).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as JSON.",
    )


def get_parser_from_args(args: argparse.Namespace) -> "LegendsParser":
    """Create a :class:`LegendsParser` from parsed CLI arguments.

    Uses ``args.xml`` if provided, otherwise auto-detects.
    """
    if args.xml:
        xml_path = args.xml
    else:
        xml_path = str(auto_detect_xml())
    return LegendsParser(xml_path)


def format_hf_summary(hf: dict, parser: "LegendsParser") -> str:
    """One-line summary of a historical figure.

    Format: ``Name (Race, Caste) [b.YEAR - d.YEAR] — associated_type``
    """
    name = hf.get("name", "Unnamed").title()
    race = (hf.get("race") or "unknown").replace("_", " ").title()
    caste = (hf.get("caste") or "").replace("_", " ").title()
    race_caste = f"{race}, {caste}" if caste else race

    birth = format_year(hf.get("birth_year"))
    death = format_year(hf.get("death_year"))
    lifespan = f"b.{birth} - d.{death}"

    assoc = hf.get("associated_type") or ""
    suffix = f" — {assoc}" if assoc else ""

    return f"{name} ({race_caste}) [{lifespan}]{suffix}"


def print_json(data: Any) -> None:
    """Pretty-print *data* as JSON to stdout."""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


# =========================================================================
# LegendsParser
# =========================================================================


class LegendsParser:
    """Lazy-loading parser for Dwarf Fortress Legends XML exports.

    Usage::

        with LegendsParser("region1-legends.xml") as lp:
            print(lp.hf_map["12345"]["name"])

    The XML is sanitized (control characters stripped) into a temporary file
    on first access. All lookup maps are built lazily via
    :func:`functools.cached_property`.
    """

    def __init__(self, xml_path: str | Path) -> None:
        self._xml_path = Path(xml_path)
        if not self._xml_path.exists():
            raise FileNotFoundError(f"XML file not found: {self._xml_path}")
        self._sanitized_path: Optional[Path] = None

    # -- Context manager ---------------------------------------------------

    def __enter__(self) -> "LegendsParser":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()

    # -- Sanitization ------------------------------------------------------

    def get_sanitized_path(self) -> Path:
        """Return the path to a sanitized copy of the XML (creates if needed).

        Control characters (0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f) are stripped
        so that the XML parser does not choke.
        """
        if self._sanitized_path and self._sanitized_path.exists():
            return self._sanitized_path

        suffix = self._xml_path.suffix or ".xml"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="legends_clean_")
        try:
            with open(self._xml_path, "rb") as src, os.fdopen(fd, "wb") as dst:
                for chunk in iter(lambda: src.read(4 * 1024 * 1024), b""):
                    cleaned = _CONTROL_CHAR_RE.sub(
                        "", chunk.decode("utf-8", errors="replace")
                    )
                    dst.write(cleaned.encode("utf-8"))
        except Exception:
            os.unlink(tmp_path)
            raise

        self._sanitized_path = Path(tmp_path)
        return self._sanitized_path

    def cleanup(self) -> None:
        """Remove the temporary sanitized XML file, if it exists."""
        if self._sanitized_path and self._sanitized_path.exists():
            try:
                self._sanitized_path.unlink()
            except OSError:
                pass
            self._sanitized_path = None

    # -- Internal iterparse helpers ----------------------------------------

    def _iterparse_section(self, outer_tag: str):
        """Yield each direct child element of *outer_tag* inside ``<df_world>``.

        Elements are cleared after yielding to keep memory low.  Depth
        tracking ensures only the immediate children of *outer_tag* are
        yielded — nested descendants are left intact so callers can read
        the full sub-tree.
        """
        path = self.get_sanitized_path()
        inside = False
        depth = 0
        for ev, elem in iterparse(str(path), events=("start", "end")):
            if not inside:
                if ev == "start" and elem.tag == outer_tag:
                    inside = True
                    depth = 0
                continue
            if ev == "start":
                depth += 1
            elif ev == "end":
                depth -= 1
                if depth < 0:
                    # We've closed the outer_tag itself — done.
                    break
                if depth == 0:
                    # Direct child of outer_tag completed.
                    yield elem
                    elem.clear()

    def _parse_flat_element(self, elem) -> dict[str, Any]:
        """Convert an XML element with simple children into a dict.

        If a child tag appears once, store as string.
        If it appears multiple times, store as list of strings.
        """
        d: dict[str, Any] = {}
        for child in elem:
            tag = child.tag
            text = (child.text or "").strip()
            if tag in d:
                existing = d[tag]
                if isinstance(existing, list):
                    existing.append(text)
                else:
                    d[tag] = [existing, text]
            else:
                d[tag] = text
        return d

    def _parse_hf_element(self, elem) -> dict[str, Any]:
        """Parse a ``<historical_figure>`` element into a rich dict."""
        hf: dict[str, Any] = {}
        list_accumulators: dict[str, list[dict]] = {}
        multi_scalar_accumulators: dict[str, list[str]] = {}

        for child in elem:
            tag = child.tag
            # Nested list structures
            if tag in _HF_LIST_TAGS:
                key = _HF_LIST_KEY[tag]
                sub = {}
                for grandchild in child:
                    sub[grandchild.tag] = (grandchild.text or "").strip()
                list_accumulators.setdefault(key, []).append(sub)
            elif tag in _HF_MULTI_SCALAR_FIELDS:
                text = (child.text or "").strip()
                multi_scalar_accumulators.setdefault(tag, []).append(text)
            else:
                text = (child.text or "").strip()
                # Handle unexpected duplicate scalar fields gracefully
                if tag in hf:
                    existing = hf[tag]
                    if isinstance(existing, list):
                        existing.append(text)
                    else:
                        hf[tag] = [existing, text]
                else:
                    hf[tag] = text

        # Merge accumulators
        for key, lst in list_accumulators.items():
            hf[key] = lst
        for key, lst in multi_scalar_accumulators.items():
            hf[key] = lst if len(lst) > 1 else lst[0]

        # Normalise boolean-ish fields.  In DF XML a self-closing tag like
        # <deity/> signals "present / true" even though its text is empty.
        for bfield in ("deity", "force"):
            if bfield in hf:
                hf[bfield] = hf[bfield] not in ("0", "false")
            else:
                hf[bfield] = False

        return hf

    def _parse_site_element(self, elem) -> dict[str, Any]:
        """Parse a ``<site>`` element, collecting structures and site_properties."""
        site: dict[str, Any] = {"structures": [], "site_properties": []}
        for child in elem:
            if child.tag == "structures":
                # <structures> is a wrapper containing <structure> children
                for struct_elem in child:
                    struct = {}
                    for gc in struct_elem:
                        struct[gc.tag] = (gc.text or "").strip()
                    site["structures"].append(struct)
            elif child.tag == "site_properties":
                # <site_properties> wrapper containing <site_property> children
                for prop_elem in child:
                    prop = {}
                    for gc in prop_elem:
                        prop[gc.tag] = (gc.text or "").strip()
                    site["site_properties"].append(prop)
            else:
                text = (child.text or "").strip()
                if child.tag in site:
                    existing = site[child.tag]
                    if isinstance(existing, list):
                        existing.append(text)
                    else:
                        site[child.tag] = [existing, text]
                else:
                    site[child.tag] = text
        return site

    def _parse_entity_element(self, elem) -> dict[str, Any]:
        """Parse an ``<entity>`` element, collecting honor as a nested list."""
        ent: dict[str, Any] = {}
        honor_list: list[dict] = []
        for child in elem:
            if child.tag == "honor":
                h = {}
                for gc in child:
                    h[gc.tag] = (gc.text or "").strip()
                honor_list.append(h)
            else:
                text = (child.text or "").strip()
                if child.tag in ent:
                    existing = ent[child.tag]
                    if isinstance(existing, list):
                        existing.append(text)
                    else:
                        ent[child.tag] = [existing, text]
                else:
                    ent[child.tag] = text
        if honor_list:
            ent["honor"] = honor_list
        return ent

    # -- Lazy-loaded properties --------------------------------------------

    @cached_property
    def hf_map(self) -> dict[str, dict]:
        """Historical figures keyed by ID string."""
        result: dict[str, dict] = {}
        for elem in self._iterparse_section("historical_figures"):
            if elem.tag != "historical_figure":
                continue
            hf = self._parse_hf_element(elem)
            hf_id = hf.get("id")
            if hf_id:
                result[str(hf_id)] = hf
        return result

    @cached_property
    def entity_map(self) -> dict[str, dict]:
        """Entities (civs, guilds, religions, site govts) keyed by ID string."""
        result: dict[str, dict] = {}
        for elem in self._iterparse_section("entities"):
            if elem.tag != "entity":
                continue
            ent = self._parse_entity_element(elem)
            eid = ent.get("id")
            if eid:
                result[str(eid)] = ent
        return result

    @cached_property
    def site_map(self) -> dict[str, dict]:
        """Sites keyed by ID string."""
        result: dict[str, dict] = {}
        for elem in self._iterparse_section("sites"):
            if elem.tag != "site":
                continue
            site = self._parse_site_element(elem)
            sid = site.get("id")
            if sid:
                result[str(sid)] = site
        return result

    @cached_property
    def artifact_map(self) -> dict[str, dict]:
        """Artifacts keyed by ID string."""
        result: dict[str, dict] = {}
        for elem in self._iterparse_section("artifacts"):
            if elem.tag != "artifact":
                continue
            art = self._parse_flat_element(elem)
            aid = art.get("id")
            if aid:
                result[str(aid)] = art
        return result

    @cached_property
    def events(self) -> list[dict]:
        """All historical events as a list of dicts."""
        result: list[dict] = []
        for elem in self._iterparse_section("historical_events"):
            if elem.tag != "historical_event":
                continue
            ev = self._parse_flat_element(elem)
            result.append(ev)
        return result

    @cached_property
    def event_collections(self) -> list[dict]:
        """All historical event collections as a list of dicts."""
        result: list[dict] = []
        for elem in self._iterparse_section("historical_event_collections"):
            if elem.tag != "historical_event_collection":
                continue
            ec = self._parse_flat_element(elem)
            result.append(ec)
        return result

    @cached_property
    def written_contents(self) -> list[dict]:
        """Written contents (poems, musical compositions, etc.)."""
        result: list[dict] = []
        for elem in self._iterparse_section("written_contents"):
            if elem.tag != "written_content":
                continue
            wc = self._parse_flat_element(elem)
            result.append(wc)
        return result

    # -- Name lookup helpers -----------------------------------------------

    def get_hf_name(self, hf_id: str) -> str:
        """Return formatted name for *hf_id*, or ``'Unknown (ID)'``."""
        hf = self.hf_map.get(str(hf_id))
        if hf and hf.get("name"):
            return hf["name"].title()
        return f"Unknown ({hf_id})"

    def get_entity_name(self, entity_id: str) -> str:
        """Return name for *entity_id*, or ``'Unknown (ID)'``."""
        ent = self.entity_map.get(str(entity_id))
        if ent and ent.get("name"):
            return ent["name"].title()
        return f"Unknown ({entity_id})"

    def get_site_name(self, site_id: str) -> str:
        """Return name for *site_id*, or ``'Unknown (ID)'``."""
        site = self.site_map.get(str(site_id))
        if site and site.get("name"):
            return site["name"].title()
        return f"Unknown ({site_id})"

    # -- Search methods ----------------------------------------------------

    def find_hf_by_name(self, name: str) -> list[dict]:
        """Case-insensitive partial match on historical figure names."""
        needle = name.lower()
        return [
            hf for hf in self.hf_map.values()
            if needle in (hf.get("name") or "").lower()
        ]

    def find_entity_by_name(self, name: str) -> list[dict]:
        """Case-insensitive partial match on entity names."""
        needle = name.lower()
        return [
            ent for ent in self.entity_map.values()
            if needle in (ent.get("name") or "").lower()
        ]

    def find_site_by_name(self, name: str) -> list[dict]:
        """Case-insensitive partial match on site names."""
        needle = name.lower()
        return [
            site for site in self.site_map.values()
            if needle in (site.get("name") or "").lower()
        ]

    def find_artifact_by_name(self, name: str) -> list[dict]:
        """Case-insensitive partial match on artifact names."""
        needle = name.lower()
        return [
            art for art in self.artifact_map.values()
            if needle in (art.get("name") or "").lower()
            or needle in (art.get("name_string") or "").lower()
        ]

    # -- Relationship queries ----------------------------------------------

    def get_entity_members(self, entity_id: str) -> list[dict]:
        """Return HF dicts that are members of *entity_id*."""
        target = str(entity_id)
        members: list[dict] = []
        for hf in self.hf_map.values():
            for link in hf.get("entity_links", []):
                if (
                    str(link.get("entity_id")) == target
                    and link.get("link_type") in (
                        "member", "position", "former member",
                        "former position", "mercenary", "prisoner",
                        "slave", "squad",
                    )
                ):
                    members.append(hf)
                    break
        return members

    # -- Event queries -----------------------------------------------------

    def _filter_year(
        self,
        event: dict,
        year_from: int | None,
        year_to: int | None,
    ) -> bool:
        """Return True if the event's year falls within the range."""
        try:
            yr = int(event.get("year", -1))
        except (ValueError, TypeError):
            return False
        if year_from is not None and yr < year_from:
            return False
        if year_to is not None and yr > year_to:
            return False
        return True

    def get_hf_events(
        self,
        hf_id: str,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[dict]:
        """Return events involving historical figure *hf_id*."""
        return [
            ev for ev in self.events
            if event_involves_hf(ev, hf_id)
            and self._filter_year(ev, year_from, year_to)
        ]

    def get_site_events(
        self,
        site_id: str,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[dict]:
        """Return events at site *site_id*."""
        return [
            ev for ev in self.events
            if event_involves_site(ev, site_id)
            and self._filter_year(ev, year_from, year_to)
        ]

    def get_entity_events(
        self,
        entity_id: str,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[dict]:
        """Return events involving entity *entity_id*."""
        return [
            ev for ev in self.events
            if event_involves_entity(ev, entity_id)
            and self._filter_year(ev, year_from, year_to)
        ]

    def filter_events(
        self,
        year_from: int | None = None,
        year_to: int | None = None,
        event_type: str | None = None,
        site_id: str | None = None,
        entity_id: str | None = None,
        hf_id: str | None = None,
    ) -> list[dict]:
        """General-purpose event filter combining multiple criteria."""
        results: list[dict] = []
        for ev in self.events:
            if not self._filter_year(ev, year_from, year_to):
                continue
            if event_type and ev.get("type") != event_type:
                continue
            if site_id and not event_involves_site(ev, site_id):
                continue
            if entity_id and not event_involves_entity(ev, entity_id):
                continue
            if hf_id and not event_involves_hf(ev, hf_id):
                continue
            results.append(ev)
        return results

    # -- Resolution helpers (name-or-ID → ID) ------------------------------

    def resolve_hf_id(self, name_or_id: str) -> str:
        """Resolve a name or numeric ID to a historical figure ID.

        Raises:
            ValueError: If the name matches zero or more than one HF.
        """
        if name_or_id.isdigit():
            return name_or_id
        matches = self.find_hf_by_name(name_or_id)
        if len(matches) == 0:
            raise ValueError(f"No historical figure found matching '{name_or_id}'")
        if len(matches) > 1:
            names = [m.get("name", "?") for m in matches[:10]]
            raise ValueError(
                f"Ambiguous: '{name_or_id}' matches {len(matches)} figures: "
                + ", ".join(names)
            )
        return str(matches[0]["id"])

    def resolve_entity_id(self, name_or_id: str) -> str:
        """Resolve a name or numeric ID to an entity ID.

        Raises:
            ValueError: If the name matches zero or more than one entity.
        """
        if name_or_id.isdigit():
            return name_or_id
        matches = self.find_entity_by_name(name_or_id)
        if len(matches) == 0:
            raise ValueError(f"No entity found matching '{name_or_id}'")
        if len(matches) > 1:
            names = [m.get("name", "?") for m in matches[:10]]
            raise ValueError(
                f"Ambiguous: '{name_or_id}' matches {len(matches)} entities: "
                + ", ".join(names)
            )
        return str(matches[0]["id"])

    def resolve_site_id(self, name_or_id: str) -> str:
        """Resolve a name or numeric ID to a site ID.

        Raises:
            ValueError: If the name matches zero or more than one site.
        """
        if name_or_id.isdigit():
            return name_or_id
        matches = self.find_site_by_name(name_or_id)
        if len(matches) == 0:
            raise ValueError(f"No site found matching '{name_or_id}'")
        if len(matches) > 1:
            names = [m.get("name", "?") for m in matches[:10]]
            raise ValueError(
                f"Ambiguous: '{name_or_id}' matches {len(matches)} sites: "
                + ", ".join(names)
            )
        return str(matches[0]["id"])
