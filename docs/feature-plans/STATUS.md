# Status and next steps

The working state: what is in work, what needs a check, small items. Decisions live in the plans;
finished work is in the git history.

_Last updated: 2026-11-15 (0001 step 5 built; step 7 on the frontier)._

## Now

- Research done: [research/2026-11-14-sources-investigation.md](research/2026-11-14-sources-investigation.md)
  (Structure Void, gluon repos, local Live installs, existing MCPs, review of ChatGPT's discovery toolkit).
- `reference/gluon-live11` and `reference/gluon-live12` cloned (shallow, git-ignored).
- Planning structure in place (this folder, `CLAUDE.md`, `docs/agents/`, `docs/guides/`), committed on `docs/plan-0001`.
- 0001 grilled (Decisions 1–27). Python 3.11.12 installed via uv (0001 decision 5).
- 0001 decided: spec and steps (2026-11-15).
- 0001 step 1 built on `feat/0001-step-1-tracer` (2026-11-15): `ableton-remote-script-mcp build-index` and
  `lookup class`; 12.4.16 indexed (283 modules, 731 classes). `uv run pytest` green (9 tests, 2 local-only).
- 0001 step 2 built on `feat/0001-step-2-extraction` (2026-11-15): full extraction (members,
  defaults, attributes, docstrings), every Remote Script and the Push 3 helper with `live_model` as a
  proxy model, index schema 2 (0001 decision 33), `list builds`. 12.4.16: 139 Remote Scripts, 1797
  modules, 4055 classes. `uv run pytest` green (22 tests, 5 local-only).
- 0001 step 3 built on `feat/0001-step-3-inheritance` (2026-11-15): inherited members with their
  origin, `search`, names resolved through re-exports and star imports at query time (0001
  decision 34, index schema 3). 12.4.16: every base resolves. `uv run pytest` green (44 tests,
  8 local-only).
- 0001 step 5 built on `feat/0001-step-5-outline` (2026-11-15): `outline <script>` (classes and
  roles, Specification fields, component map, mappings, elements, components, layers); the
  extractor records a statement summary of each function (0001 decision 35, index schema 4;
  rebuild older indexes), with the conditions each statement runs under, kept in a separate
  `live-<build>.statements.json` so the API index stays names and signatures (user story 14
  amended). `uv run pytest` green (60 tests, 10 local-only).
- [ready-for-agent] **0001 step 7** — validator: basic checks. Next in this session, after a `/compact`.

## After grilling

- Steps are built in this same session, with a `/compact` between steps (0001 decision 31).
- Order: 1 → 2 → 3 → 5 → 7 → 9 → 9a → 8 → 10 → 4 → 6 → 11 → 12.

## Small items

- [ready-for-human] Set the GitHub repo description and topics (0001 decision 27).
- [ready-for-human] Archive `ableton-remote-script-skill` on GitHub; its README already points here (commit 3100c40 by the skill-repo session, 2026-11-15) (0001 decision 21).

## Backlog

- (empty)
