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
- `reference/` (git-ignored): local clones of gluon's decompiled Live 11.2.11 and Live 12 scripts (12.0-era framework, nine recent controllers from 12's Python 3.11 bytecode), `MidiFighterV3`, `PrismScript` and `APC40_MkII_StepSequencer_v1.*` (no licence, local only), `beatstep` (raphaelquast's Beatstep_Q, GPL-3.0) and `clyphx-live11` (ldrolez's ClyphX, LGPL-3.0); read those two, don't copy their code into the MIT repos, for reading framework internals and real-world scripts.
- Installed Live apps, the primary API source: `/Applications/Ableton Live 12 Suite.app` (12.4.16), `… 12 Beta.app` (12.4.25b1), `… 13 Beta.app` (13.0b25). Scripts are under `Contents/App-Resources/MIDI Remote Scripts/`, Python 3.11 `.pyc` only.

## Agent team

**Solo mode is the default** (user, 2026-11-19, for cost): `scripts/agents.sh` starts only the
architect, which plans and builds one task per fresh session and calls `reviewer` and `docs` as
subagents. Peer sessions are for parallel work; they message each other (`SendMessage`), run in
tmux, and start only when named (plan 0001 Decision 54):

| Name | Agent file | Model | Job |
|---|---|---|---|
| `arsm-architect` | `.claude/agents/architect.md` | opus | lead: plans, STATUS, tasks and briefs, decisions, merges |
| `arsm-core` | `.claude/agents/core.md` | sonnet | index, query and answer core, API, MCP server, validator, stubs — **on demand** |
| `arsm-reviewer` | `.claude/agents/reviewer.md` | opus | read-only review against the plans and the Ableton-material rules — **on demand** (a subagent in solo mode) |
| `arsm-docs` | `.claude/agents/docs.md` | sonnet | docs site and README — **on demand** |
| `arsm-skill` | `.claude/agents/skill.md` | sonnet | the skill and its evals — **on demand** |
| `arsm-rig` | `.claude/agents/rig.md` | sonnet | the test rig, plan 0002 — **on demand** |

Flow: architect → builder (or docs, with a brief) → reviewer (→ architect for a decision the
plans don't cover) → the builder commits → a short overview to the architect, who updates the
plan and STATUS on the same branch → the user gets what to try by hand.

- **One agent per area;** each agent file names its own. Before editing, check `git diff <file>`
  and don't touch a file with another agent's uncommitted changes.
- **One working tree, one index:** the architect picks the branch, nobody else switches. Commit
  your own files by path, `git commit -- <files>` (a new file: `git add <file>` right before);
  never `git add -A`, never a bare `git commit` after staging.
- **Plans and STATUS are the architect's.** A builder's overview says what they should now say;
  the architect writes it on the same branch before a merge, so "in sync" holds per branch.
- **Only the architect merges into `main`, and only when the user asks. Only the user pushes.**
- **Live:** the test rig's exceptions below are used by one agent at a time, the one the architect
  names, after the user has said in this session that the rig's port is picked.
- **Clean sessions, as often as possible** (user, 2026-11-19): one task, one fresh builder
  session, stopped once its task is committed; no agent but the architect is ever compacted. A
  builder whose context grows long mid-task hands over and asks for a fresh start. The reviewer
  starts fresh for each feature. The architect suggests a fresh architect (or a ready-to-paste
  `/compact` line) after every finished task. So the hand-over always lives in files: the task
  text, the plan, STATUS.
- **A message to an agent that isn't running** goes to `arsm-architect`, naming the intended
  agent; the architect starts it or handles it.
- `scripts/agents.sh` starts the architect in your pane, **fresh** (its agent file, this file and
  STATUS are the hand-over). `scripts/agents.sh core rig` (any of core, reviewer, docs, skill,
  rig) starts peers in the tmux window `arsm-agents`; `--resume <agent>` continues a recorded
  session; `status` and `stop` as in the script's header.

## Rules that hold everywhere

- **Every API fact carries its Live build and a confidence:**
  - `observed`: present in the index of that build.
  - `tested`: used by a minimal script that loaded in that build.
  - `documented`: from a secondary source only (Structure Void, forum, decompiled reference).

  Generated code and skill guidance build on `observed` or `tested` facts; a `documented` fact is labelled as such until it is checked.
- **Ableton's code and anything extracted from it stay local.** This covers the `.pyc` files, decompiled sources, the API index data and the runtime dumps. They live in git-ignored folders (`reference/`, the index output). The repos publish tools, the skill and our own writing.
- **Live 13 beta findings stay out of anything published** until the beta terms allow it.
- **Structure Void's docs are CC BY-NC-SA 4.0:** cite them and write in our own words.
- **Only the user operates Live:** selecting a control surface, restarting, and connecting hardware are the user's actions. An agent reads `~/Library/Preferences/Ableton/Live <version>/Log.txt` and tells the user what to do in Live. One exception, for the test rig only (plan 0002 Decision 1): once the user has picked the rig's virtual port, the agent may send MIDI to that port and change the open test Set, never save it. It may also capture Live's window (only that window) to decide a visual check, and deletes the image after reading (plan 0002 Decision 22). And it may restart Live with `rig restart-live`, only while Live shows just the unsaved test Set, answering "Don't Save" and never saving (Decision 23).
- Decisions are dated and say who decided. A changed decision gets a new dated line, and a contradiction with a decided plan is raised, never silently overridden.
- Keep plans, STATUS and code in sync in the same change.
