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
- `examples/APC_mini_mk1_Plus/`: a git submodule, the APC mini mk1 script `APC_mini_mk1_Plus` (the drum sequencer, plan 0003 Decision 36). Its own repo (`MarvinHauke/APC_mini_mk1_Plus`), MIT, one repo per controller. The submodule is the only working copy: its `origin` is GitHub, so run `git switch main` in it before editing. Its `stubs/` (from `build-stubs`, git-ignored) are local only. A fresh clone needs `git submodule update --init` and the push guard `git config push.recurseSubmodules check` (local config: a push of `main` here fails while the pinned commit is not on GitHub). To follow the script's newest `main`: `git submodule update --remote --merge` (`.gitmodules` names `branch = main`; `--merge` keeps it on the branch). Ownership is the same as for the other examples: the script code is arsm-skill's, `checks.yaml` and `device.yaml` are arsm-rig's. Commit inside the submodule first, then commit the new submodule pointer here. Its README follows the same Ableton-material rules. Only the architect pushes it, after a commit there, and only when the user says so.
- `docs/agents/`: configuration for the mattpocock skills (tracker, triage labels, domain docs).
- `reference/` (git-ignored): local clones of gluon's decompiled Live 11.2.11 and Live 12 scripts (12.0-era framework, nine recent controllers from 12's Python 3.11 bytecode), `MidiFighterV3`, `PrismScript` and `APC40_MkII_StepSequencer_v1.*` (no licence, local only), `beatstep` (raphaelquast's Beatstep_Q, GPL-3.0) and `clyphx-live11` (ldrolez's ClyphX, LGPL-3.0); read those two, don't copy their code into the MIT repos, for reading framework internals and real-world scripts.
- Installed Live apps, the primary API source: `/Applications/Ableton Live 12 Suite.app` (12.4.16), `… 12 Beta.app` (12.4.25b1), `… 13 Beta.app` (13.0b25). Scripts are under `Contents/App-Resources/MIDI Remote Scripts/`, Python 3.11 `.pyc` only.

## Agent team

**Solo mode is the default** (user, 2026-11-19, for cost): `scripts/agents.sh` starts only the
architect, which plans and builds one task per fresh session, starts the reviewer as a peer in
its own window before each commit (user, 2026-11-19: the user follows the review there) and calls
`docs` as a subagent. Peer sessions are for parallel work; they message each other (`SendMessage`), run in
tmux, and start only when named (plan 0001 Decision 54):

| Name | Agent file | Model | Job |
|---|---|---|---|
| `arsm-architect` | `.claude/agents/architect.md` | opus | lead: plans, STATUS, tasks and briefs, decisions, merges |
| `arsm-core` | `.claude/agents/core.md` | sonnet | index, query and answer core, API, MCP server, validator, stubs — **on demand** |
| `arsm-reviewer` | `.claude/agents/reviewer.md` | opus | read-only review against the plans and the Ableton-material rules — **on demand** (a peer in its own window, also in solo mode) |
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
- **Only the architect merges into `main`, and only when the user asks. Only the architect pushes,
  and only `main` after a merge** (user, 2026-11-19: "you should be able to push by yourself").
  No agent force-pushes, pushes another branch or opens a pull request unless the user asks.
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

## Working in the script's submodule

`examples/APC_mini_mk1_Plus` is its own git repo (plan 0003 Decision 36). The repo rules above
hold in it too, with these additions (architect, 2026-11-19):

- **Branch:** for a task that touches the script, the architect creates a branch of the same name
  in both repos (`git -C examples/APC_mini_mk1_Plus switch -c <branch>`). Builders don't switch
  branches in either repo.
- **Commit there first, by path, relative to the submodule:**
  `git -C examples/APC_mini_mk1_Plus commit -- APC_mini_mk1_Plus/<file>`. A `git commit` here
  can't take paths inside the submodule. The pointer `examples/APC_mini_mk1_Plus` is committed
  here, together with the plan and STATUS, once the script's commit is in.
- **Review:** `git -C examples/APC_mini_mk1_Plus status --short` and `git -C
  examples/APC_mini_mk1_Plus diff` (or `git diff --submodule=diff` here) show the script's change.
  The pointer here must match the script's commit.
- **Merge and push** (architect, only when the user asks): first merge the script repo's branch
  into its `main` and push it, then commit the pointer here, merge and push `main`. The guard
  `push.recurseSubmodules = check` refuses the wrong order.
- **Not in its commits:** `stubs/` (from Ableton's code, git-ignored).

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
