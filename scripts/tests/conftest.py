"""Shared pytest fixtures for Legends XML parser tests.

Provides a small but complete sample XML document and a pre-loaded
LegendsParser instance that all test modules can use.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Ensure the DF root is on sys.path so ``from scripts.legends_parser import ...`` works.
_DF_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_DF_ROOT))

from scripts.legends_parser import LegendsParser  # noqa: E402

# ---------------------------------------------------------------------------
# Minimal but comprehensive sample XML
# ---------------------------------------------------------------------------
# Entities:
#   100 = "the guilds of testing" (dwarf civ)
#   101 = "the work of tests"     (site government)
#   102 = "the dark horde"        (goblin civ)
#
# Sites:
#   200 = "testfort"  (fortress, coords 10,20)
#   201 = "evilspire" (dark fortress)
#
# Historical figures:
#   300 = "urist mctest"     — dwarf, male, planter, alive, member of 100+101
#   301 = "dorin shieldarm"  — dwarf, female, fighter, alive, spouse of 300
#   302 = "snagak goretooth" — goblin, male, enemy, dead (year 101)
#   303 = "blaze firemaw"    — dragon, male, megabeast, dead (year 50)
#   304 = "kiddo mctest"     — dwarf, male, child of 300+301, alive
#
# Artifacts:
#   400 = "gleamcutter" — held by 300, at site 200
#   401 = "darkbane"    — no holder, at site 200
#
# Events cover: created site, change hf state, artifact created,
#   artifact stored, masterpiece item, hf died, add hf entity link,
#   add hf hf link, merchant, hf simple battle event
#
# Event collections: 1 war (500), 1 battle (501)
#
# Written content: 1 poem (600)
# ---------------------------------------------------------------------------

SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<df_world>
<regions>
<region><id>1</id><name>the northern hills</name><type>Hills</type></region>
</regions>
<underground_regions>
<underground_region><id>1</id><depth>1</depth><type>cavern</type></underground_region>
</underground_regions>
<sites>
<site>
  <id>200</id><type>fortress</type><name>testfort</name>
  <coords>10,20</coords><rectangle>160,320:163,323</rectangle>
  <structures>
    <structure><local_id>0</local_id><type>inn tavern</type><name>the copper mug</name></structure>
    <structure><local_id>1</local_id><type>temple</type><name>the holy anvil</name><entity_id>100</entity_id></structure>
  </structures>
  <site_properties>
    <site_property><structure_id>0</structure_id><owner_hfid>300</owner_hfid></site_property>
  </site_properties>
</site>
<site>
  <id>201</id><type>dark fortress</type><name>evilspire</name>
  <coords>50,50</coords><rectangle>800,800:803,803</rectangle>
  <structures></structures>
  <site_properties></site_properties>
</site>
</sites>
<world_constructions></world_constructions>
<artifacts>
<artifact>
  <id>400</id><name>gleamcutter</name><name_string>gleamcutter</name_string>
  <item>weapon</item><holder_hfid>300</holder_hfid><site_id>200</site_id>
  <structure_local_id>-1</structure_local_id>
</artifact>
<artifact>
  <id>401</id><name>darkbane</name><name_string>darkbane the fiery sunset</name_string>
  <item>shield</item><holder_hfid>-1</holder_hfid><site_id>200</site_id>
  <structure_local_id>0</structure_local_id>
</artifact>
</artifacts>
<historical_figures>
<historical_figure>
  <id>300</id><name>urist mctest</name><race>DWARF</race><caste>MALE</caste>
  <appeared>1</appeared>
  <birth_year>40</birth_year><birth_seconds72>-1</birth_seconds72>
  <death_year>-1</death_year><death_seconds72>-1</death_seconds72>
  <associated_type>PLANTER</associated_type>
  <entity_link><link_type>member</link_type><entity_id>100</entity_id></entity_link>
  <entity_link><link_type>member</link_type><entity_id>101</entity_id></entity_link>
  <entity_position_link>
    <position_profile_id>3</position_profile_id><entity_id>101</entity_id>
    <start_year>99</start_year><end_year>-1</end_year>
  </entity_position_link>
  <hf_link><link_type>spouse</link_type><hfid>301</hfid><link_strength>100</link_strength></hf_link>
  <hf_link><link_type>child</link_type><hfid>304</hfid></hf_link>
  <hf_link><link_type>deity</link_type><hfid>303</hfid><link_strength>50</link_strength></hf_link>
  <hf_skill><skill>PLANT</skill><total_ip>16000</total_ip></hf_skill>
  <hf_skill><skill>MINING</skill><total_ip>3000</total_ip></hf_skill>
  <hf_skill><skill>RECORD_KEEPING</skill><total_ip>5500</total_ip></hf_skill>
  <hf_skill><skill>WRESTLING</skill><total_ip>500</total_ip></hf_skill>
  <holds_artifact>400</holds_artifact>
  <sphere>agriculture</sphere>
  <goal>CREATE_A_GREAT_WORK_OF_ART</goal>
</historical_figure>
<historical_figure>
  <id>301</id><name>dorin shieldarm</name><race>DWARF</race><caste>FEMALE</caste>
  <appeared>1</appeared>
  <birth_year>38</birth_year><birth_seconds72>-1</birth_seconds72>
  <death_year>-1</death_year><death_seconds72>-1</death_seconds72>
  <associated_type>HAMMERMAN</associated_type>
  <entity_link><link_type>member</link_type><entity_id>100</entity_id></entity_link>
  <entity_link><link_type>member</link_type><entity_id>101</entity_id></entity_link>
  <hf_link><link_type>spouse</link_type><hfid>300</hfid><link_strength>100</link_strength></hf_link>
  <hf_link><link_type>child</link_type><hfid>304</hfid></hf_link>
  <hf_skill><skill>HAMMER</skill><total_ip>18700</total_ip></hf_skill>
  <hf_skill><skill>DODGING</skill><total_ip>8200</total_ip></hf_skill>
  <hf_skill><skill>SHIELD</skill><total_ip>5700</total_ip></hf_skill>
  <hf_skill><skill>ARMOR</skill><total_ip>3700</total_ip></hf_skill>
</historical_figure>
<historical_figure>
  <id>302</id><name>snagak goretooth</name><race>GOBLIN</race><caste>MALE</caste>
  <appeared>1</appeared>
  <birth_year>10</birth_year><birth_seconds72>-1</birth_seconds72>
  <death_year>101</death_year><death_seconds72>54000</death_seconds72>
  <associated_type>LASHER</associated_type>
  <entity_link><link_type>member</link_type><entity_id>102</entity_id></entity_link>
  <entity_link><link_type>enemy</link_type><entity_id>100</entity_id></entity_link>
  <hf_skill><skill>WHIP</skill><total_ip>23500</total_ip></hf_skill>
</historical_figure>
<historical_figure>
  <id>303</id><name>blaze firemaw the tax of sweltering</name>
  <race>DRAGON</race><caste>MALE</caste>
  <appeared>1</appeared>
  <birth_year>-50</birth_year><birth_seconds72>-1</birth_seconds72>
  <death_year>50</death_year><death_seconds72>-1</death_seconds72>
  <associated_type>STANDARD</associated_type>
  <entity_link><link_type>enemy</link_type><entity_id>100</entity_id></entity_link>
  <entity_link><link_type>enemy</link_type><entity_id>102</entity_id></entity_link>
  <sphere>fire</sphere><sphere>wealth</sphere>
  <deity/>
</historical_figure>
<historical_figure>
  <id>304</id><name>kiddo mctest</name><race>DWARF</race><caste>MALE</caste>
  <appeared>1</appeared>
  <birth_year>80</birth_year><birth_seconds72>-1</birth_seconds72>
  <death_year>-1</death_year><death_seconds72>-1</death_seconds72>
  <associated_type>STANDARD</associated_type>
  <entity_link><link_type>member</link_type><entity_id>100</entity_id></entity_link>
  <hf_link><link_type>father</link_type><hfid>300</hfid></hf_link>
  <hf_link><link_type>mother</link_type><hfid>301</hfid></hf_link>
</historical_figure>
</historical_figures>
<entity_populations>
<entity_population><id>1</id></entity_population>
</entity_populations>
<entities>
<entity><id>100</id><name>the guilds of testing</name></entity>
<entity><id>101</id><name>the work of tests</name></entity>
<entity><id>102</id><name>the dark horde</name></entity>
</entities>
<historical_events>
<historical_event>
  <id>1000</id><year>99</year><seconds72>100</seconds72><type>created site</type>
  <civ_id>100</civ_id><site_civ_id>101</site_civ_id><site_id>200</site_id>
</historical_event>
<historical_event>
  <id>1001</id><year>99</year><seconds72>200</seconds72><type>change hf state</type>
  <hfid>300</hfid><site_id>200</site_id><state>settled</state><mood>-1</mood>
</historical_event>
<historical_event>
  <id>1002</id><year>99</year><seconds72>200</seconds72><type>change hf state</type>
  <hfid>301</hfid><site_id>200</site_id><state>settled</state><mood>-1</mood>
</historical_event>
<historical_event>
  <id>1003</id><year>99</year><seconds72>300</seconds72><type>add hf entity link</type>
  <hfid>300</hfid><civ_id>101</civ_id><link_type>position</link_type>
  <position_id>3</position_id>
</historical_event>
<historical_event>
  <id>1004</id><year>100</year><seconds72>500</seconds72><type>artifact created</type>
  <hfid>300</hfid><artifact_id>400</artifact_id><site_id>200</site_id>
</historical_event>
<historical_event>
  <id>1005</id><year>100</year><seconds72>600</seconds72><type>artifact stored</type>
  <artifact_id>400</artifact_id><site_id>200</site_id><unit_id>-1</unit_id>
</historical_event>
<historical_event>
  <id>1006</id><year>100</year><seconds72>700</seconds72><type>artifact created</type>
  <hfid>301</hfid><artifact_id>401</artifact_id><site_id>200</site_id>
</historical_event>
<historical_event>
  <id>1007</id><year>100</year><seconds72>1000</seconds72><type>masterpiece item</type>
  <hfid>300</hfid><entity_id>101</entity_id><site_id>200</site_id>
  <skill_at_time>14</skill_at_time><maker_hfid>300</maker_hfid>
</historical_event>
<historical_event>
  <id>1008</id><year>100</year><seconds72>1500</seconds72><type>masterpiece item</type>
  <hfid>300</hfid><entity_id>101</entity_id><site_id>200</site_id>
  <skill_at_time>14</skill_at_time><maker_hfid>300</maker_hfid>
</historical_event>
<historical_event>
  <id>1009</id><year>101</year><seconds72>10000</seconds72><type>merchant</type>
  <site_id>200</site_id><trader_hfid>-1</trader_hfid><trader_entity_id>100</trader_entity_id>
</historical_event>
<historical_event>
  <id>1010</id><year>101</year><seconds72>50000</seconds72>
  <type>hf simple battle event</type>
  <group_1_hfid>301</group_1_hfid><group_2_hfid>302</group_2_hfid>
  <site_id>200</site_id><subregion_id>-1</subregion_id>
</historical_event>
<historical_event>
  <id>1011</id><year>101</year><seconds72>54000</seconds72><type>hf died</type>
  <hfid>302</hfid><slayer_hfid>301</slayer_hfid><site_id>200</site_id>
  <cause>struck</cause><slayer_race>DWARF</slayer_race><slayer_caste>FEMALE</slayer_caste>
</historical_event>
<historical_event>
  <id>1012</id><year>101</year><seconds72>55000</seconds72>
  <type>add hf hf link</type>
  <hfid>300</hfid><hfid_target>301</hfid_target>
  <link_type>spouse</link_type>
</historical_event>
<historical_event>
  <id>1013</id><year>102</year><seconds72>1000</seconds72><type>masterpiece item</type>
  <hfid>301</hfid><entity_id>101</entity_id><site_id>200</site_id>
  <skill_at_time>28</skill_at_time><maker_hfid>301</maker_hfid>
</historical_event>
<historical_event>
  <id>1014</id><year>102</year><seconds72>2000</seconds72>
  <type>change hf state</type>
  <hfid>304</hfid><site_id>200</site_id><state>settled</state><mood>-1</mood>
</historical_event>
</historical_events>
<historical_event_collections>
<historical_event_collection>
  <id>500</id><type>war</type><name>the test war</name>
  <start_year>101</start_year><start_seconds72>40000</start_seconds72>
  <end_year>-1</end_year><end_seconds72>-1</end_seconds72>
  <aggressor_ent_id>102</aggressor_ent_id><defender_ent_id>100</defender_ent_id>
  <eventcol>501</eventcol>
</historical_event_collection>
<historical_event_collection>
  <id>501</id><type>battle</type><name>the siege of testfort</name>
  <start_year>101</start_year><start_seconds72>50000</start_seconds72>
  <end_year>101</end_year><end_seconds72>54000</end_seconds72>
  <attacking_enid>102</attacking_enid><defending_enid>100</defending_enid>
  <attacking_squad_number>5</attacking_squad_number>
  <attacking_squad_deaths>1</attacking_squad_deaths>
  <attacking_squad_race>GOBLIN</attacking_squad_race>
  <defending_squad_number>3</defending_squad_number>
  <defending_squad_deaths>0</defending_squad_deaths>
  <defending_squad_race>DWARF</defending_squad_race>
  <event>1010</event><event>1011</event>
  <coords>10,20</coords>
</historical_event_collection>
</historical_event_collections>
<historical_eras>
<historical_era><name>The Age of Testing</name><start_year>0</start_year></historical_era>
</historical_eras>
<written_contents>
<written_content>
  <id>600</id><title>ode to a plump helmet</title>
  <author_hfid>300</author_hfid><form>poem</form><form_id>1</form_id>
  <style>self_indulgent</style><author_roll>0</author_roll>
</written_content>
</written_contents>
<poetic_forms>
<poetic_form><id>1</id><description>a simple verse form</description></poetic_form>
</poetic_forms>
<musical_forms>
<musical_form><id>1</id><description>a simple melody</description></musical_form>
</musical_forms>
<dance_forms>
<dance_form><id>1</id><description>a simple jig</description></dance_form>
</dance_forms>
</df_world>
"""

# ---------------------------------------------------------------------------
# Constants for test assertions
# ---------------------------------------------------------------------------
# HF IDs
URIST_ID = "300"
DORIN_ID = "301"
SNAGAK_ID = "302"
DRAGON_ID = "303"
KIDDO_ID = "304"

# Entity IDs
DWARF_CIV_ID = "100"
SITE_GOV_ID = "101"
GOBLIN_CIV_ID = "102"

# Site IDs
TESTFORT_ID = "200"
EVILSPIRE_ID = "201"

# Artifact IDs
GLEAMCUTTER_ID = "400"
DARKBANE_ID = "401"

# War/battle IDs
WAR_ID = "500"
BATTLE_ID = "501"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sample_xml_path(tmp_path_factory: pytest.TempPathFactory) -> Generator[Path, None, None]:
    """Write the sample XML to a temp file and yield its path."""
    tmp = tmp_path_factory.mktemp("legends")
    xml_path = tmp / "region-test-legends.xml"
    xml_path.write_text(SAMPLE_XML, encoding="utf-8")
    yield xml_path


@pytest.fixture(scope="session")
def parser(sample_xml_path: Path) -> Generator[LegendsParser, None, None]:
    """Provide a fully-loaded LegendsParser for the sample XML."""
    with LegendsParser(str(sample_xml_path)) as lp:
        yield lp


@pytest.fixture()
def df_root() -> Path:
    """Return the Dwarf Fortress root directory."""
    return _DF_ROOT
