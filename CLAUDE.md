# Ableton Remote Script assistant

A development-time assistant for **writing Ableton Live MIDI Remote Scripts** (control surfaces). It has three parts:
- a per-version **API index** of Live's Remote Script framework and the `Live` module
- a coding **skill**
- an **MCP server** over the index

It controls nothing at runtime; that is AbletonMCP's job. The architecture is plan
`docs/feature-plans/0001-architecture.md` (stage and frontier in its header and in `STATUS.md`).

## Where things are

- `docs/feature-plans/`: plans and their dated decisions (`README.md` is the index, `STATUS.md` the working state, `GLOSSARY.md` the shared language). Use the glossary's words in plans, code and docs.
- `docs/feature-plans/research/`: cited source investigations. Read `2026-11-14-sources-investigation.md` before working on the index, the skill or the MCP.
- `docs/guides/skills-workflow.md`: how a feature runs (draft → grill → spec → steps → build → review → test).
- `docs/agents/`: configuration for the mattpocock skills (tracker, triage labels, domain docs).
- `reference/` (git-ignored): local clones of gluon's decompiled Live 11.2.11 and Live 12 scripts (12.0-era framework, nine recent controllers from 12's Python 3.11 bytecode), and `MidiFighterV3` (no licence, local only), for reading framework internals.
- Installed Live apps, the primary API source: `/Applications/Ableton Live 12 Suite.app` (12.4.16), `… 12 Beta.app` (12.4.25b1), `… 13 Beta.app` (13.0b25). Scripts are under `Contents/App-Resources/MIDI Remote Scripts/`, Python 3.11 `.pyc` only.

## Rules that hold everywhere

- **Every API fact carries its Live build and a confidence:**
  - `observed`: present in the index of that build.
  - `tested`: used by a minimal script that loaded in that build.
  - `documented`: from a secondary source only (Structure Void, forum, decompiled reference).

  Generated code and skill guidance build on `observed` or `tested` facts; a `documented` fact is labelled as such until it is checked.
- **Ableton's code and anything extracted from it stay local.** This covers the `.pyc` files, decompiled sources, the API index data and the runtime dumps. They live in git-ignored folders (`reference/`, the index output). The repos publish tools, the skill and our own writing.
- **Live 13 beta findings stay out of anything published** until the beta terms allow it.
- **Structure Void's docs are CC BY-NC-SA 4.0:** cite them and write in our own words.
- **Only the user operates Live:** selecting a control surface, restarting, and connecting hardware are the user's actions. An agent reads `~/Library/Preferences/Ableton/Live <version>/Log.txt` and tells the user what to do in Live.
- Decisions are dated and say who decided. A changed decision gets a new dated line, and a contradiction with a decided plan is raised, never silently overridden.
- Keep plans, STATUS and code in sync in the same change.
