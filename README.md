# The Chronicles of Luregold

A living, in-character chronicle of a Dwarf Fortress playthrough, written from the perspective of the fortress bookkeeper. Accompanied by a set of Python scripts for extracting and querying the game's Legends XML export.

---

## The Chronicle

The chronicle is a first-person manuscript written by **Atir Dumatturel** — called "Roughlearning" — bookkeeper, Grandmaster Planter, and one of the seven founding dwarves of the fortress of Luregold. It is not a wiki. It is not omniscient. It is the biased, opinionated, frequently wine-stained account of one dwarf who takes his ledger seriously even while mocking himself for it.

### Table of Contents

| # | File | Description |
|---|------|-------------|
| — | [Preamble](chronicle/luregold-000-intro.md) | Who the bookkeeper is, who the Guilds of Clinching are, the founding seven, and the essential deep history — the fall of Bookbalded, the wars that nearly ended everything, and the moment seven dwarves decided to walk into the wilderness with one pick and a collective failure of judgment. |
| 100 | [Year 100 — The Year We Struck Earth](chronicle/luregold-100.md) | The founding. Seven dwarves, one pick, twenty-five active wars on the continent, and somehow nobody dies. First migrants arrive. First artifacts forged. The ledger begins. |
| 101 | [Year 101 — The Second Annual Review](chronicle/luregold-101.md) | The fortress swells from nineteen to seventy-odd settlers. Ushrir Beardedspears begins her extraordinary masterwork spree. Sibrek becomes a reluctant soldier. The first real threats arrive — and are met. |
| 102 | [Year 102 — The Third Annual Review](chronicle/luregold-102.md) | Eighty-eight settlers. Zero deaths. Rovod Cobaltfortunes walks through the gate and produces 141 masterworks in under a year. A three-year-old arrives at a frontier fortress during a world war. The bookkeeper is concerned by the lack of things to be concerned about. |

> *"The ink stains on this page are ink. The other stains are plump helmet wine. I will not be taking questions."*
> — Atir Dumatturel

---

## Scripts

A set of Python scripts in [`scripts/`](scripts/) for parsing and querying the Dwarf Fortress **Legends XML** export. Python 3.10+ required; no external dependencies.

All scripts auto-detect the most recent `region*-legends.xml` in the current directory (or accept `--xml PATH`), and support `--year`, `--year-from`, `--year-to`, and `--json` flags.

| Script | Purpose |
|--------|---------|
| `legends_parser.py` | Core library — shared parser, lookup maps, name resolution. Not run directly. |
| `whats_new.py` | Events since year N, grouped by year/season/category. The recommended starting point. |
| `events.py` | General event browser with flexible filtering (type, site, entity, figure). |
| `civilization.py` | Civilization overview — population, sites, wars, notable members. |
| `site.py` | Site/fortress overview — structures, residents, artifacts, event timeline. |
| `creature.py` | Creature/historical figure lookup — bio, affiliations, kills, events. |
| `figure.py` | Historical figure profile — identity, positions, skills, family, artifacts. |
| `figure_relations.py` | Relationships — family tree, social links, deity worship. |
| `figure_skills.py` | Skills table with category grouping and side-by-side comparison. |
| `relationship_history.py` | Shared history between two or more figures — events, memberships, family network. |
| `artifact.py` | Artifact lookup — creator, holder, location, event history. |
| `battle.py` | Wars and battles — list, filter, or get full details for event collections. |
| `deaths.py` | Death/obituary tracker — who died, how, when, and by whose hand. |
| `migrations.py` | Migration wave tracker — settlers grouped by arrival wave with profiles. |
| `population.py` | Population census — arrivals, deaths, departures, running totals by year. |
| `moods.py` | Strange moods, artifact creation, and masterwork production by figure. |
| `megabeasts.py` | Megabeast/forgotten beast/titan/demon tracker, sorted by kill count. |
| `interactions.py` | Entity-to-entity interaction log — wars, battles, trade, diplomacy. |

### Quick Start

```powershell
# What happened since year 101?
python scripts/whats_new.py --since-year 101

# Who lives at Luregold?
python scripts/site.py luregold --residents

# Look up the bookkeeper
python scripts/creature.py "atir roughlearning" --events

# Deaths in year 102
python scripts/deaths.py --year 102 --site luregold
```
