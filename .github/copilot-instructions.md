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

The Dwarf Fortress Legends XML export contains structured data about the entire world history. When you need to extract specific information:

- **Write a targeted Python script** that parses only the XML elements you need. Use `xml.etree.ElementTree` with `iterparse` for large files. Do not try to load the whole file into memory at once.
- **Ask the player** for the file path — it changes with each export.
- **Ask the player** for anything you can't find in the XML. Some information (fortress layout, social dynamics, mood descriptions, specific in-game observations) exists only in the player's memory or save file.
- Common useful XML paths:
  - `/df_world/historical_events/historical_event` — timestamped events (battles, deaths, artifact creation, site conquests)
  - `/df_world/historical_figures/historical_figure` — individual characters with relationships, skills, kills
  - `/df_world/entities/entity` — civilizations, site governments, guilds, religions
  - `/df_world/sites/site` — fortresses, towns, lairs with population and ownership
  - `/df_world/artifacts/artifact` — named artifacts with creator and description
  - `/df_world/entity_populations/entity_population` — population counts by race at each site
  - `/df_world/historical_event_collections/historical_event_collection` — wars, battles, event groupings

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