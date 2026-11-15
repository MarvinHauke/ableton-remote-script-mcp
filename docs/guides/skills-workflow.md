# Working with the mattpocock skills

Adapted from the UC4 Editor (`~/Development/web/UC4_Editor/docs/guides/skills-workflow.md`) for a
smaller setup: one planning session, plus a fresh builder session per step (0001 Q16).

User-invoked skills (**/**) are typed by you in the planning session; the session says when one
is due. Model-invoked skills are called by the agents themselves.

| Artifact | Place |
|---|---|
| Shared language | `docs/feature-plans/GLOSSARY.md` |
| Designs, decisions (dated, with why), specs | `docs/feature-plans/NNNN-*.md` |
| Plan index and order | `docs/feature-plans/README.md` |
| Tickets | numbered **steps** in the plan |
| Working state, small items, backlog | `docs/feature-plans/STATUS.md` |
| Research | `docs/feature-plans/research/` |

## A feature, step by step

```
draft ─▶ grill ─▶ spec ─▶ steps ─▶ build ─▶ review ─▶ test ─▶ ship
```

1. **Draft:** the planning session writes `NNNN-*.md` from `TEMPLATE.md`: problem, design, open
   questions with a recommended answer each.
2. **Grill:** "grill me on NNNN" (`grilling` + `domain-modeling`, as `/grill-with-docs`). It runs
   in rounds of numbered questions, and "yes" accepts a recommendation. The agent looks facts up
   itself and brings only decisions to you. Terms land in the glossary as they settle, and answers
   become dated decisions. It ends when no branch is open and you confirm.
3. **Spec:** `/to-spec` gives the plan the spec shape and confirms the test seams.
4. **Steps:** `/to-tickets` cuts it into tracer-bullet steps, each demoable, each naming its
   blockers.
5. **Build:** a fresh builder session takes one step: `tdd` at the agreed seams, `diagnosing-bugs`
   for hard failures, `codebase-design` for interfaces.
6. **Review:** `code-review`. Standards = `CLAUDE.md` and the plan's decisions; Spec = the step.
7. **Test:** what can run here runs here. Anything in Live goes to you as a short list, while the
   agent reads `Log.txt`.
8. **Ship:** when you ask, the PR body is written with `pr`.

## Work that isn't a feature

| Situation | Skill |
|---|---|
| Too big or too unknown for one plan | **/wayfinder** (`.scratch/<effort>/`) |
| Primary-source facts | `research` → `docs/feature-plans/research/` |
| "What should this look like?" | `prototype` (throwaway) |
| Steps only you can do (in Live) | `wizard` |
| New findings and bug reports | **/triage** → STATUS |
| Ending a long session | **/handoff** |
