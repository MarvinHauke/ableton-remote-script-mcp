# Issue tracker: feature plans and STATUS

Work is tracked in the feature plans and `docs/feature-plans/STATUS.md`, not GitHub Issues.

- **Spec:** a numbered plan, `docs/feature-plans/NNNN-<slug>.md`; the next number comes from the
  index in `docs/feature-plans/README.md`.
- **Ticket:** a step in the plan's "Steps", plus one line in `STATUS.md` ("Now" while in work,
  "Small items" or "Backlog" otherwise).
- **Triage state:** a tag at the start of the STATUS line, e.g. `[ready-for-agent]`
  (`triage-labels.md`).
- **Comments and open points:** the plan's "Open questions".

When a skill says "publish to the issue tracker": a feature becomes a plan draft, and a small thing
becomes a STATUS line. When it says "fetch the ticket": read the named plan step and its STATUS
line.

**Wayfinding** (`/wayfinder`): the map is `.scratch/<effort>/map.md` and the child tickets are
`.scratch/<effort>/issues/NN-<slug>.md` (git-ignored). When the effort resolves, its decisions move
into a plan and the folder is deleted.
