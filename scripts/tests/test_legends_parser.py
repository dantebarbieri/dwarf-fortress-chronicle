"""Tests for the core legends_parser.py module.

Uses the sample XML fixture from conftest.py.
Run with: python -m pytest scripts/tests/test_legends_parser.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure DF root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from scripts.legends_parser import (
    LegendsParser,
    auto_detect_xml,
    event_involves_entity,
    event_involves_hf,
    event_involves_site,
    format_hf_summary,
    format_year,
    skill_level_name,
)
from scripts.tests.conftest import (
    URIST_ID,
    DORIN_ID,
    SNAGAK_ID,
    DRAGON_ID,
    KIDDO_ID,
    DWARF_CIV_ID,
    SITE_GOV_ID,
    GOBLIN_CIV_ID,
    TESTFORT_ID,
    EVILSPIRE_ID,
    GLEAMCUTTER_ID,
    DARKBANE_ID,
    WAR_ID,
    BATTLE_ID,
)


# =========================================================================
# Map Loading
# =========================================================================


class TestMapLoading:
    def test_hf_map_count(self, parser):
        assert len(parser.hf_map) == 5

    def test_hf_map_urist(self, parser):
        hf = parser.hf_map[URIST_ID]
        assert hf["name"] == "urist mctest"
        assert hf["race"] == "DWARF"
        assert hf["caste"] == "MALE"
        assert hf["birth_year"] == "40"
        assert hf["death_year"] == "-1"
        assert hf["associated_type"] == "PLANTER"

    def test_hf_map_urist_entity_links(self, parser):
        hf = parser.hf_map[URIST_ID]
        links = hf["entity_links"]
        assert len(links) == 2
        ids = {link["entity_id"] for link in links}
        assert ids == {DWARF_CIV_ID, SITE_GOV_ID}
        assert all(link["link_type"] == "member" for link in links)

    def test_hf_map_urist_hf_links(self, parser):
        hf = parser.hf_map[URIST_ID]
        links = hf["hf_links"]
        assert len(links) == 3
        link_types = {link["link_type"] for link in links}
        assert link_types == {"spouse", "child", "deity"}

    def test_hf_map_urist_skills(self, parser):
        hf = parser.hf_map[URIST_ID]
        skills = hf["hf_skills"]
        assert len(skills) == 4
        plant_skill = next(s for s in skills if s["skill"] == "PLANT")
        assert plant_skill["total_ip"] == "16000"

    def test_hf_map_dragon_deity(self, parser):
        hf = parser.hf_map[DRAGON_ID]
        assert hf["deity"] is True

    def test_hf_map_dragon_spheres(self, parser):
        hf = parser.hf_map[DRAGON_ID]
        assert hf["sphere"] == ["fire", "wealth"]

    def test_entity_map_count(self, parser):
        assert len(parser.entity_map) == 3

    def test_entity_map_names(self, parser):
        assert parser.entity_map[DWARF_CIV_ID]["name"] == "the guilds of testing"
        assert parser.entity_map[SITE_GOV_ID]["name"] == "the work of tests"
        assert parser.entity_map[GOBLIN_CIV_ID]["name"] == "the dark horde"

    def test_site_map_count(self, parser):
        assert len(parser.site_map) == 2

    def test_site_map_structures(self, parser):
        site = parser.site_map[TESTFORT_ID]
        structs = site["structures"]
        assert len(structs) == 2
        assert structs[0]["type"] == "inn tavern"
        assert structs[0]["name"] == "the copper mug"
        assert structs[1]["type"] == "temple"
        assert structs[1]["name"] == "the holy anvil"

    def test_site_map_site_properties(self, parser):
        site = parser.site_map[TESTFORT_ID]
        props = site["site_properties"]
        assert len(props) == 1

    def test_artifact_map_count(self, parser):
        assert len(parser.artifact_map) == 2

    def test_artifact_map_gleamcutter(self, parser):
        art = parser.artifact_map[GLEAMCUTTER_ID]
        assert art["name"] == "gleamcutter"
        assert art["holder_hfid"] == URIST_ID
        assert art["site_id"] == TESTFORT_ID

    def test_events_count(self, parser):
        assert len(parser.events) == 15

    def test_event_collections_count(self, parser):
        assert len(parser.event_collections) == 2

    def test_written_contents_count(self, parser):
        assert len(parser.written_contents) == 1


# =========================================================================
# Name Search
# =========================================================================


class TestNameSearch:
    def test_find_hf_by_name_exact(self, parser):
        results = parser.find_hf_by_name("urist mctest")
        assert len(results) == 1
        assert results[0]["id"] == URIST_ID

    def test_find_hf_by_name_partial(self, parser):
        results = parser.find_hf_by_name("mctest")
        assert len(results) == 2
        ids = {r["id"] for r in results}
        assert ids == {URIST_ID, KIDDO_ID}

    def test_find_hf_by_name_case_insensitive(self, parser):
        results = parser.find_hf_by_name("URIST")
        assert len(results) == 1

    def test_find_hf_by_name_no_match(self, parser):
        results = parser.find_hf_by_name("nonexistent")
        assert results == []

    def test_find_entity_by_name(self, parser):
        results = parser.find_entity_by_name("guilds")
        assert len(results) == 1

    def test_find_site_by_name(self, parser):
        results = parser.find_site_by_name("testfort")
        assert len(results) == 1

    def test_find_artifact_by_name(self, parser):
        results = parser.find_artifact_by_name("gleamcutter")
        assert len(results) == 1

    def test_find_artifact_by_name_string(self, parser):
        results = parser.find_artifact_by_name("fiery sunset")
        assert len(results) == 1
        assert results[0]["id"] == DARKBANE_ID


# =========================================================================
# Resolution
# =========================================================================


class TestResolution:
    def test_resolve_hf_id_numeric(self, parser):
        assert parser.resolve_hf_id("300") == "300"

    def test_resolve_hf_id_name(self, parser):
        assert parser.resolve_hf_id("urist mctest") == URIST_ID

    def test_resolve_hf_id_ambiguous(self, parser):
        with pytest.raises(ValueError, match="Ambiguous"):
            parser.resolve_hf_id("mctest")

    def test_resolve_hf_id_not_found(self, parser):
        with pytest.raises(ValueError, match="No historical figure"):
            parser.resolve_hf_id("zzzzz")

    def test_resolve_entity_id(self, parser):
        assert parser.resolve_entity_id("guilds of testing") == DWARF_CIV_ID

    def test_resolve_site_id(self, parser):
        assert parser.resolve_site_id("testfort") == TESTFORT_ID


# =========================================================================
# Name Helpers
# =========================================================================


class TestNameHelpers:
    def test_get_hf_name(self, parser):
        assert parser.get_hf_name(URIST_ID) == "Urist Mctest"

    def test_get_hf_name_unknown(self, parser):
        assert parser.get_hf_name("999") == "Unknown (999)"

    def test_get_entity_name(self, parser):
        assert parser.get_entity_name(DWARF_CIV_ID) == "The Guilds Of Testing"

    def test_get_site_name(self, parser):
        assert parser.get_site_name(TESTFORT_ID) == "Testfort"


# =========================================================================
# Entity Members
# =========================================================================


class TestEntityMembers:
    def test_get_entity_members_civ(self, parser):
        members = parser.get_entity_members(DWARF_CIV_ID)
        member_ids = {m["id"] for m in members}
        assert len(members) == 3
        assert member_ids == {URIST_ID, DORIN_ID, KIDDO_ID}

    def test_get_entity_members_site_gov(self, parser):
        members = parser.get_entity_members(SITE_GOV_ID)
        member_ids = {m["id"] for m in members}
        assert len(members) == 2
        assert member_ids == {URIST_ID, DORIN_ID}


# =========================================================================
# Event Filtering
# =========================================================================


class TestEventFiltering:
    def test_get_hf_events_urist(self, parser):
        events = parser.get_hf_events(URIST_ID)
        assert len(events) == 6

    def test_get_site_events_testfort(self, parser):
        events = parser.get_site_events(TESTFORT_ID)
        assert len(events) == 13

    def test_get_entity_events(self, parser):
        events = parser.get_entity_events(DWARF_CIV_ID)
        assert len(events) >= 1

    def test_filter_events_year(self, parser):
        events = parser.filter_events(year_from=101, year_to=101)
        assert all(ev["year"] == "101" for ev in events)
        assert len(events) == 4

    def test_filter_events_year_range(self, parser):
        events = parser.filter_events(year_from=100, year_to=101)
        assert len(events) == 9

    def test_filter_events_type(self, parser):
        events = parser.filter_events(event_type="hf died")
        assert len(events) == 1

    def test_filter_events_combined(self, parser):
        events = parser.filter_events(
            year_from=100, year_to=100, site_id=TESTFORT_ID
        )
        assert len(events) == 5
        assert all(ev["year"] == "100" for ev in events)

    def test_event_involves_hf(self, parser):
        died_events = [e for e in parser.events if e.get("type") == "hf died"]
        assert len(died_events) == 1
        ev = died_events[0]
        assert event_involves_hf(ev, SNAGAK_ID)  # hfid
        assert event_involves_hf(ev, DORIN_ID)  # slayer_hfid

    def test_event_involves_entity(self, parser):
        created = [e for e in parser.events if e.get("type") == "created site"]
        assert len(created) == 1
        ev = created[0]
        assert event_involves_entity(ev, DWARF_CIV_ID)

    def test_event_involves_site(self, parser):
        masterpiece = [
            e for e in parser.events if e.get("type") == "masterpiece item"
        ]
        assert len(masterpiece) > 0
        ev = masterpiece[0]
        assert event_involves_site(ev, TESTFORT_ID)


# =========================================================================
# Utility Functions
# =========================================================================


class TestUtilityFunctions:
    def test_skill_level_name_dabbling(self):
        assert skill_level_name(0) == "Dabbling"

    def test_skill_level_name_novice(self):
        assert skill_level_name(500) == "Novice"

    def test_skill_level_name_legendary(self):
        assert skill_level_name(53100) == "Legendary"

    def test_skill_level_name_legendary_plus(self):
        assert skill_level_name(53500) == "Legendary+1"

    def test_format_year_normal(self):
        assert format_year("101") == "101"

    def test_format_year_present(self):
        assert format_year("-1") == "present"

    def test_format_year_none(self):
        assert format_year(None) == "?"

    def test_format_hf_summary(self, parser):
        hf = parser.hf_map[URIST_ID]
        summary = format_hf_summary(hf, parser)
        assert "Urist Mctest" in summary
        assert "Dwarf" in summary
        assert "Male" in summary
        assert "b.40" in summary
        assert "d.present" in summary
        assert "PLANTER" in summary


# =========================================================================
# Auto-detect
# =========================================================================


class TestAutoDetect:
    def test_auto_detect_xml(self, tmp_path):
        xml_file = tmp_path / "region1-00100-legends.xml"
        xml_file.write_text("<df_world></df_world>", encoding="utf-8")
        result = auto_detect_xml(tmp_path)
        assert result == xml_file

    def test_auto_detect_xml_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            auto_detect_xml(tmp_path)


# =========================================================================
# Context Manager
# =========================================================================


class TestContextManager:
    def test_context_manager_cleanup(self, sample_xml_path):
        with LegendsParser(str(sample_xml_path)) as lp:
            _ = lp.hf_map  # trigger sanitization
            sanitized = lp._sanitized_path
            assert sanitized is not None
            assert sanitized.exists()
        assert not sanitized.exists()


# =========================================================================
# Empty World (empty_world.xml)
# =========================================================================


class TestEmptyWorld:
    """Loading empty_world.xml should produce empty maps without errors."""

    def test_empty_hf_map(self, empty_world_xml_path):
        with LegendsParser(str(empty_world_xml_path)) as lp:
            assert len(lp.hf_map) == 0

    def test_empty_entity_map(self, empty_world_xml_path):
        with LegendsParser(str(empty_world_xml_path)) as lp:
            assert len(lp.entity_map) == 0

    def test_empty_site_map(self, empty_world_xml_path):
        with LegendsParser(str(empty_world_xml_path)) as lp:
            assert len(lp.site_map) == 0

    def test_empty_artifact_map(self, empty_world_xml_path):
        with LegendsParser(str(empty_world_xml_path)) as lp:
            assert len(lp.artifact_map) == 0

    def test_empty_events(self, empty_world_xml_path):
        with LegendsParser(str(empty_world_xml_path)) as lp:
            assert len(lp.events) == 0

    def test_empty_event_collections(self, empty_world_xml_path):
        with LegendsParser(str(empty_world_xml_path)) as lp:
            assert len(lp.event_collections) == 0

    def test_empty_written_contents(self, empty_world_xml_path):
        with LegendsParser(str(empty_world_xml_path)) as lp:
            assert len(lp.written_contents) == 0


# =========================================================================
# Dead Figures (dead_figures.xml)
# =========================================================================


class TestDeadFigures:
    """Dead HFs in dead_figures.xml should have correct death_year != -1."""

    def test_dead_figure_count(self, dead_figures_xml_path):
        with LegendsParser(str(dead_figures_xml_path)) as lp:
            dead = [hf for hf in lp.hf_map.values() if hf["death_year"] != "-1"]
            assert len(dead) == 5, f"Expected 5 dead figures, got {len(dead)}"

    def test_alive_figure_count(self, dead_figures_xml_path):
        with LegendsParser(str(dead_figures_xml_path)) as lp:
            alive = [hf for hf in lp.hf_map.values() if hf["death_year"] == "-1"]
            assert len(alive) == 2, f"Expected 2 alive figures, got {len(alive)}"

    def test_ingiz_death_year(self, dead_figures_xml_path):
        with LegendsParser(str(dead_figures_xml_path)) as lp:
            hf = lp.hf_map["710"]
            assert hf["death_year"] == "95"

    def test_erush_death_year_old_age(self, dead_figures_xml_path):
        with LegendsParser(str(dead_figures_xml_path)) as lp:
            hf = lp.hf_map["712"]
            assert hf["death_year"] == "80"

    def test_bomrek_death_year_drowned(self, dead_figures_xml_path):
        with LegendsParser(str(dead_figures_xml_path)) as lp:
            hf = lp.hf_map["715"]
            assert hf["death_year"] == "85"

    def test_death_events_have_correct_causes(self, dead_figures_xml_path):
        with LegendsParser(str(dead_figures_xml_path)) as lp:
            died_events = [e for e in lp.events if e.get("type") == "hf died"]
            causes = {e.get("hfid"): e.get("cause") for e in died_events}
            assert causes["710"] == "struck"
            assert causes["712"] == "old age"
            assert causes["715"] == "drowned"
            assert causes["716"] == "thirst"


# =========================================================================
# Year-range filtering with peaceful_years.xml (gap years)
# =========================================================================


class TestPeacefulYearsFiltering:
    """peaceful_years.xml has events in year 50 and 100 only — gap years
    between them should return empty results."""

    def test_gap_year_returns_empty(self, peaceful_years_xml_path):
        with LegendsParser(str(peaceful_years_xml_path)) as lp:
            events = lp.filter_events(year_from=60, year_to=90)
            assert len(events) == 0, "Gap years 60-90 should have no events"

    def test_year_50_has_events(self, peaceful_years_xml_path):
        with LegendsParser(str(peaceful_years_xml_path)) as lp:
            events = lp.filter_events(year_from=50, year_to=50)
            assert len(events) == 4

    def test_year_100_has_events(self, peaceful_years_xml_path):
        with LegendsParser(str(peaceful_years_xml_path)) as lp:
            events = lp.filter_events(year_from=100, year_to=100)
            assert len(events) == 2

    def test_full_range_includes_all(self, peaceful_years_xml_path):
        with LegendsParser(str(peaceful_years_xml_path)) as lp:
            events = lp.filter_events(year_from=1, year_to=200)
            assert len(events) == 6
