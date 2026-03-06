# Luregold Chronicle — Project Instructions

This file provides persistent context for AI assistants working on the Dwarf Fortress chronicle project. Read this before making any changes to files in `chronicle/`.

---

## What This Project Is

A living, in-character journal/manuscript set in the world of Dwarf Fortress. The chronicle is written from the perspective of the fortress bookkeeper and is periodically extended as the player exports new Legends XML data from the game. The file is **not** a wiki, encyclopedia, or omniscient narrative — it is a **first-person document** produced by a character with limited, biased, and sometimes drunken knowledge.

The source data comes from:
- **Dwarf Fortress Legends Mode XML export** — the canonical record of world events, populations, artifacts, kills, relationships, etc.
- **In-game observations** — things the player notices during gameplay that aren't captured cleanly in the XML (moods, social dynamics, layout details). The player will provide these as context when requesting updates.

---

## File Structure

The chronicle lives in `chronicle/` and is split into separate files:

| File | Contents |
|------|----------|
| `luregold-intro.md` | Preamble: who the bookkeeper is, who the Guilds of Clinching are, the founding seven, essential deep history (Notchedgalley, Bookbalded, Cavechew, pre-founding wars). Ends at the moment the seven set out. |
| `luregold-100.md` | Year 100 annual review. |
| `luregold-101.md` | Year 101 annual review. |
| `luregold-102.md` | Year 102 annual review (current). |
| `luregold-[NNN].md` | Future years, one file per year. |

### Why separate files
- **Smaller context** — the AI can grab just the file it needs instead of loading the full history.
- **Create, don't edit** — when extending or correcting, recreate the single affected file from scratch rather than trying to edit it in place. Creation is more reliable than surgical edits.
- **Natural in-world framing** — each year file is an annual ledger review, the kind of document a bookkeeper would actually produce.

### How the files relate
- `luregold-intro.md` is the foundation. It provides the context needed to understand any year file.
- Each year file is **self-contained enough to read on its own** but assumes the reader has access to the intro and prior years. Light cross-references are fine: "as I noted in last year's review," "I will have more to say when the spring caravan arrives."
- The **most recent year file** is always the active one. It ends mid-stream — no epilogue, no closing, no capstone. Just the latest entry.

### When updating a year in progress
If the player exports new XML mid-year, **recreate** the current year's file with the new entries appended. Read the existing file first to maintain continuity, then write the whole file fresh. Do not attempt to append or edit in place.

### When a new year begins
Create a new file `luregold-[YEAR].md`. Read the previous year's file and the intro for context. The new file opens with Atir noting the turn of the year and begins the new annual review.

---

## The Current Bookkeeper

**Atir Dumatturel**, called "Roughlearning." Grandmaster Planter, Adept Record Keeper, co-founder of the Guild of Leopards (farmers' guild), and one of the seven founding dwarves of the fortress of Luregold. He is the narrator and sole author of the chronicle.

### Voice characteristics
- Dry, self-deprecating humor. Drinks heavily (plump helmet wine). Knows it. Doesn't care.
- Opinionated. Has strong views on everyone and states them as editorial asides, margin notes, or parentheticals.
- Genuine respect for competence — admires Solon's quiet skill, Ushrir's prolific craft, Sibrek's reluctant courage — but expresses it sideways, never sentimentally.
- His relationship with Mayor Unib Townveiled is the emotional spine of the chronicle: two old acquaintances who drink together, argue about policy, and never say they're friends.
- He takes his bookkeeping seriously even while mocking himself for it. The ledger is sacred. The numbers matter.
- He uses the third person ("the Bookkeeper recommends...") when being formal/official, first person when being personal.

### What Atir knows and how he knows it
Atir's knowledge is bounded by what a fortress bookkeeper would realistically have access to. He is not omniscient. He does not have access to a wiki. He pieces together the world from:
1. His own eyes and memory (most reliable)
2. The fortress ledger and records he maintains (reliable, exact)
3. Conversations with specific named dwarves (reliable but colored by the speaker)
4. Reports from migrants arriving at Luregold (secondhand, sometimes unreliable)
5. Gossip from trading caravans (thirdhand, often contradictory)
6. Deep history and legends passed down through oral tradition or fragmentary records (least reliable)

**Every piece of information in the chronicle should be attributable to one of these sources.** When writing or extending, always ask: *how would Atir know this?*

---

## Number Fidelity Gradient

Numbers should be more precise the closer they are to Atir's direct experience, and vaguer the further away. This is the core mechanic that makes the document feel like an in-world artifact rather than a data dump.

| Source | Fidelity | Examples |
|--------|----------|---------|
| Luregold internal (population, stockpiles, masterworks, artifacts, deaths) | **Exact** | "88 settlers," "866 masterworks," "413 by Ushrir's hand," "zero deaths" |
| Luregold events Atir witnessed | **Exact** | "Zutthan struck once with weapon #694," "the goblin was 158 years old" |
| Luregold events Atir heard about secondhand | **Mostly exact, with hedging** | "Sibrek — or so the dining hall tells it — killed the creature with his hands" |
| Clinching-wide stats (civ population, total dead, site counts) | **Rounded / approximate** | "some seven hundred dwarves," "over three hundred buried," "thirty-odd sites" |
| Named battles/wars in Clinching history | **Named but with fuzzy details** | "a hundred and fifty dead, or near enough — the records from Bookbalded are incomplete" |
| Foreign civilization populations and battle counts | **Vague** | "fewer than a hundred humans remain," "dozens of battles," "scores of dead" |
| Megabeast/demon kill tallies | **Impressionistic** | "the demon has killed more of our people than any living creature," "the Roc has taken lives across the continent" |
| Forgotten Beast counts | **Unknown to Atir** | "the deep miners speak of hundreds," "I have no count and no wish for one" |
| Distant wars Atir has no stake in | **Hearsay** | "the elves and goblins are at each other's throats — which elves and which goblins depends on who you ask" |

When pulling exact numbers from the XML to write new entries, **always filter them through this gradient before committing them to the chronicle.**

---

## Document Formatting

### Use
- **Dated journal entries** — the primary unit. Each entry has a date (Year and Season/Month at minimum) and covers what Atir learned or observed during that period.
- **In-character section titles** that sound like manuscript marginalia: *"On the Matter of Goblins," "What the Autumn Caravan Told Me," "A Reckoning of the Dead," "The Five Objects That Should Not Exist."*
- **Margin notes** — short asides, warnings, or drunk commentary. Rendered as block quotes or italicized parentheticals.
- **Inserted folios / retrospectives** — longer sections where Atir compiles information on a topic. Still written in his voice, still attributed to sources.
- **The ledger** — Atir occasionally quotes from or references the official fortress ledger, which has a drier, more formal tone than his personal voice.

### Do not use
- Markdown tables for data presentation (Atir writes prose, possibly with indented lists)
- Emoji or unicode symbols in headers
- Threat-level color coding (🔴🟠🟡🟢)
- Numbered chapter headers ("CHAPTER X:")
- Any structural element that implies an omniscient editorial perspective

---

## Continuation Protocol

### Extending the chronicle
1. Read `copilot-instructions.md` (this file).
2. Read the current year's file and the intro to get Atir's most recent tone and concerns.
3. Accept new data from the player (XML export path, in-game observations, or summary of events).
4. If using XML, write a targeted Python script to extract relevant new events. Use `xml.etree.ElementTree` with `iterparse` for large files. Focus on changes since the last known date.
5. **Recreate** the current year's file (or create a new year file) from scratch with the new entries incorporated. Do not attempt to append or surgically edit.
6. Apply the number-fidelity gradient and source-attribution rules.
7. Do not rewrite earlier year files unless the player specifically asks for corrections.
8. If Atir would not plausibly know something, either omit it or have him note the gap. ("I have heard nothing of the Lancer of Rumors since the autumn migrants. This worries me more than news would.")

### When the bookkeeper dies
If the player reports that Atir has died in-game, the chronicle transitions to a new bookkeeper. The new author:
- Begins with a brief note acknowledging the transition ("I found this manuscript in the bookkeeper's quarters, beside an empty wine barrel...")
- Writes in their **own** distinct voice — different from Atir's
- May comment on or disagree with Atir's assessments
- Continues the same structural conventions (dated entries, source attribution, number fidelity, annual files)
- The death entry and the transition note can appear in the same year file — no special file is needed
- The player will provide the new bookkeeper's name, skills, and personality traits

**Do not pre-write the transition.** It happens only when the player says it has happened.

---

## Working with the Legends XML

The Dwarf Fortress Legends XML export contains structured data about the entire world history. A set of reusable Python scripts lives in `scripts/` to parse and extract data from these exports.

### Prerequisites

- **Python 3.10+** (standard library only — no external dependencies)
- All scripts are run from the **Dwarf Fortress root directory** (the one containing `Dwarf Fortress.exe`)
- On Windows, set UTF-8 console encoding for proper display: `[Console]::OutputEncoding = [Text.Encoding]::UTF8` or set `$env:PYTHONIOENCODING = "utf-8"`

### XML Auto-Detection

All scripts accept `--xml PATH` to specify the Legends XML file. If omitted, they auto-detect the most recent `region*-legends.xml` file in the current directory.

### Common Parameters

Every script supports these via `--help`:

| Parameter | Description |
|-----------|-------------|
| `--xml PATH` | Path to the Legends XML export |
| `--year N` | Filter to a single year |
| `--year-from N` | Start of year range (inclusive) |
| `--year-to N` | End of year range (inclusive) |
| `--json` | Output results as JSON (for piping to other tools) |

### Naming Convention

The XML uses **English translation names**, not dwarven names. For example, the bookkeeper Atir Dumatturel appears as `atir roughlearning` in the XML. When searching by name, use the English translation. Partial, case-insensitive matching is supported by all scripts.

### Scripts Reference

#### `scripts/legends_parser.py` — Core Module

Shared library imported by all other scripts. Not run directly. Provides:
- `LegendsParser` class with lazy-loaded lookup maps (`hf_map`, `entity_map`, `site_map`, `artifact_map`, `events`, `event_collections`)
- XML sanitization (strips control characters that break the parser)
- Name resolution, event filtering, skill level conversion
- Context manager support (`with LegendsParser(path) as lp:`)

#### `scripts/filter_civilization.py` — Civilization Overview

```
python scripts/filter_civilization.py "guilds of clinching"
python scripts/filter_civilization.py 258 --members --wars --sites
python scripts/filter_civilization.py "guilds of clinching" --year-from 100 --json
```

| Parameter | Description |
|-----------|-------------|
| `name` (positional) | Civilization name or entity ID |
| `--members` | Show member list |
| `--wars` | Show war details |
| `--sites` | Show owned sites |

Shows: overview, population (alive/dead, by race), sites, notable members, wars, recent events.

#### `scripts/filter_fortress.py` — Site/Fortress Overview

```
python scripts/filter_fortress.py luregold
python scripts/filter_fortress.py luregold --structures --residents --events
python scripts/filter_fortress.py 794 --year 102
```

| Parameter | Description |
|-----------|-------------|
| `name` (positional) | Site name or ID |
| `--structures` | Show structure details |
| `--residents` | Show linked historical figures |
| `--events` | Show full event timeline |

Shows: site overview, structures, owning entities, artifacts, event summary, resident figures.

#### `scripts/filter_creature.py` — Creature/Historical Figure Lookup

```
python scripts/filter_creature.py "atir roughlearning"
python scripts/filter_creature.py "ebbak" --events --kills
python scripts/filter_creature.py "atir" --list
```

| Parameter | Description |
|-----------|-------------|
| `name` (positional) | Creature/figure name or HF ID |
| `--events` | Show full event timeline |
| `--kills` | Show kill list |
| `--list` | List all matches (for ambiguous names) |

Shows: bio, entity affiliations, positions, relationships, skills, held artifacts, kills, events.

#### `scripts/filter_year.py` — Events by Year

```
python scripts/filter_year.py --year 102
python scripts/filter_year.py --year-from 100 --year-to 102 --site luregold
python scripts/filter_year.py --year 101 --type "hf died" --summary
```

| Parameter | Description |
|-----------|-------------|
| `--type TYPE` | Filter by event type (partial match) |
| `--site SITE` | Filter by site name or ID |
| `--entity ENTITY` | Filter by entity name or ID |
| `--figure FIGURE` | Filter by historical figure name or ID |
| `--summary` | Show count-by-type summary instead of listing events |
| `--limit N` | Maximum events to show |

At least one year filter (`--year`, `--year-from`, or `--year-to`) is required.

#### `scripts/dwarf.py` — Dwarf/Figure Profile

```
python scripts/dwarf.py "atir roughlearning"
python scripts/dwarf.py 14589 --race DWARF
```

| Parameter | Description |
|-----------|-------------|
| `name` (positional) | Figure name or HF ID |
| `--race RACE` | Filter matches to a specific race |

Shows: identity, status, entity memberships, positions held, top skills, family, held artifacts, goals, event summary.

#### `scripts/dwarf_relations.py` — Relationships

```
python scripts/dwarf_relations.py "atir roughlearning"
python scripts/dwarf_relations.py "atir roughlearning" --tree
python scripts/dwarf_relations.py 14589 --all
```

| Parameter | Description |
|-----------|-------------|
| `name` (positional) | Figure name or HF ID |
| `--tree` | Show ASCII family tree (2 generations) |
| `--all` | Include all relationship types (including enemies) |

Shows: family (spouse, children, parents), deity links, social links (master/apprentice/companion), entity relationships, relationship events.

#### `scripts/dwarf_skills.py` — Skills

```
python scripts/dwarf_skills.py "atir roughlearning"
python scripts/dwarf_skills.py "ushrir beardedspears" --min-level Skilled
python scripts/dwarf_skills.py "atir roughlearning" --compare "ushrir beardedspears"
```

| Parameter | Description |
|-----------|-------------|
| `name` (positional) | Figure name or HF ID |
| `--sort {level,name,ip}` | Sort order (default: level/IP descending) |
| `--min-level LEVEL` | Only show skills at or above this level |
| `--compare NAME` | Compare skills side-by-side with another figure |

Shows: skills table (skill, level, IP), masterpiece events, skills grouped by category (combat, military, social, craft/labor).

#### `scripts/artifact.py` — Artifacts

```
python scripts/artifact.py
python scripts/artifact.py "ripedepressed"
python scripts/artifact.py --site luregold --list
python scripts/artifact.py --holder 14589
```

| Parameter | Description |
|-----------|-------------|
| `name` (positional, optional) | Artifact name or ID. Omit to list all. |
| `--site SITE` | Filter by site name or ID |
| `--holder HOLDER` | Filter by holder name or ID |
| `--list` | Force list mode |

List mode: table of all artifacts. Detail mode: full artifact info with creator, holder, location, and chronological event history.

#### `scripts/battle.py` — Wars & Battles

```
python scripts/battle.py wars
python scripts/battle.py wars --entity "guilds of clinching" --active
python scripts/battle.py battles --year 102 --site luregold
python scripts/battle.py detail 5316
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `wars` | List wars (filterable by `--entity`, `--active`, year) |
| `battles` | List battles (filterable by `--entity`, `--site`, year) |
| `detail ID` | Show full details for a specific event collection |

| Parameter | Description |
|-----------|-------------|
| `--entity NAME` | Filter by participating entity |
| `--site NAME` | Filter by site |
| `--active` | Only show ongoing wars/battles |

#### `scripts/events.py` — General Event Browser

```
python scripts/events.py --year 102 --site luregold
python scripts/events.py --type "hf died" --year-from 100
python scripts/events.py --figure "atir roughlearning" --summary
python scripts/events.py --types
```

| Parameter | Description |
|-----------|-------------|
| `--type TYPE` | Filter by event type (partial match) |
| `--site SITE` | Filter by site name or ID |
| `--entity ENTITY` | Filter by entity name or ID |
| `--figure FIGURE` | Filter by historical figure name or ID |
| `--summary` | Count-by-type summary |
| `--types` | List all event types and exit |
| `--raw` | Show raw event dictionaries |
| `--limit N` | Max events (default: 100) |

At least one filter is required. Provides human-readable descriptions for 30+ event types.

#### `scripts/relationship_history.py` — Relationship History Between Figures

```
python scripts/relationship_history.py "atir roughlearning" "unib townveiled"
python scripts/relationship_history.py 1234 5678 9012 --events
python scripts/relationship_history.py "atir roughlearning" "unib townveiled" --events --year-from 100
```

| Parameter | Description |
|-----------|-------------|
| `names` (positional, 2+) | Two or more figure names or HF IDs |
| `--events` | Show full shared event timeline |
| `--include-indirect` | Include events involving figures related to the subjects |

Shows: direct relationships, shared entity memberships, shared site connections, shared events, family network (BFS up to 3 hops for 2 figures), chronological timeline summary. Useful for understanding pairs (e.g., Atir and Unib), squads of invaders, or why a migrant arrived without family.

### Writing Custom Extraction Scripts

When writing new scripts for one-off extractions:

1. Import from the core module:
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
   from scripts.legends_parser import (
       LegendsParser, add_common_args, get_parser_from_args,
       configure_output, print_json, format_hf_summary
   )
   ```
2. Use `iterparse` for memory efficiency on the ~63 MB file
3. Focus on changes since the last known date when extending the chronicle
4. Apply the number-fidelity gradient and source-attribution rules from this document

### Known IDs (Current Save)

| Entity | XML ID |
|--------|--------|
| Luregold (fortress) | site 794 |
| The Guilds of Clinching (civilization) | entity 258 |
| The Work of Sides (site government) | entity 1188 |
| Luregold artifacts | artifacts 611–615 |

---

## Checklist Before Committing Changes

- [ ] All numbers pass the fidelity gradient (exact for Luregold, vague for distant)
- [ ] Every claim is attributable to a plausible source Atir would have access to
- [ ] No omniscient perspective or wiki-style formatting
- [ ] No epilogue or closing statement in the most recent year file
- [ ] Atir's voice is consistent (dry humor, wine, opinions, the Unib dynamic)
- [ ] No content was lost from the source material
- [ ] No character or event is described with overlapping text across files
- [ ] The affected file was **created fresh**, not edited in place