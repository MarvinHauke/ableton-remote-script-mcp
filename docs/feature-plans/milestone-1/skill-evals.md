# Skill evals: the baseline round and the step 10 round

Plan 0001 step 9a, run 2026-11-16 against Live 12.4.16. Each case ran three times with the skill
v1 and three times without it, with `/skill-creator`'s case format and `claude plugin eval`. This
page holds the setup, the scores and what they mean for the next steps (Decision 42).

## The cases

Under `skills/ableton-remote-scripts/evals/`, one folder each, with the prompt as a user would
type it and one grader per checked statement:

| Case | Task | Framework asked for |
|---|---|---|
| `apc-mini-mk1-clip-launcher` | clip grid, scene launch, track stop, faders, Shift + track buttons move the box; device facts from Akai's protocol in the prompt | none (the run chooses) |
| `uc4-mixer-v3` | 8-track mixer (volume, pan, mute, crossfader, bank buttons) for the Faderfox UC4, setup 1 factory settings, from the UC4 Editor's device facts | `ableton.v3` |
| `port-v2-pads-to-v3` | port `Pad_Box_16`, a small `ableton.v2` script written for the evals (4x4 pads, 4 faders, 4 navigation buttons), to v3 | `ableton.v3` |

## How the runs were scored

- **Behaviour graders:** statements about the script and the answer (the top grid row is the
  first scene, the MIDI numbers come from the prompt, the answer says how to load the script),
  judged by the eval command's judge from the run's trace and files.
- **Validator findings:** `ableton-remote-script-mcp validate` on each script folder the run
  wrote.
- **Unknown names:** `scripts/eval_names.py` sorts every attribute name and every keyword
  argument of a framework constructor into one of five groups: names the script defines itself,
  Python's own names, names in the index, names Ableton's own scripts use in a call, and unknown
  names. The unknown names are the candidates for invented names. The check works by name, not
  by class: a name that any indexed class has counts as known on every object. Keywords are
  checked only on constructors of a class imported by name, not on method calls or
  `module.Class(...)`, and only where the `__init__` chain shows every keyword it takes (about
  half of the v3 classes, not v3's `SessionComponent`).
- **"Known" is wider than the plan's "in the index":** besides the index's classes, modules,
  members and parameter names, a name also counts as known when Ableton's own scripts use it in
  a call (the statement summaries). That covers the `Live` objects' attributes, which the index
  does not list.

The judge cannot run the validator or the name check, so `scripts/eval_score.py` overwrites its
verdicts on those two graders with the real scores. `scripts/eval_run.sh` runs the whole round,
against Live 12.4.16 unless `EVAL_BUILD` says otherwise.

**The sandbox:** the eval command runs each case in a sandbox that cannot read `/Users`, apart from
the skill's folder and a few `bin` folders.
- **No repo for the runs:** none of them could read this repo, and the example script
  `examples/APC_mini_mk1` would have answered the APC case. `eval_score.py` checks each trace for
  reads of the repo and found none. The review of this round also checked the traces by hand: no
  run without the skill touched the CLI, the index copy or the skill's `evals/`, and the scorer
  now flags those too.
- **A copy of the CLI for the skill:** the skill's scripts need the CLI and the index, so
  `eval_run.sh` puts a self-contained build of the CLI and a copy of the index into `~/.local/bin`
  for the length of the round and removes them afterwards. The runs without the skill never learn
  they are there.
- **The installed Live is readable:** `/Applications` is readable inside the sandbox, so every run
  could read the installed Live's `.pyc` files.
- **Nothing is left behind:** the round's sandboxes held the traces, with output from Live's
  `.pyc` files. `eval_run.sh` now copies each trace into the git-ignored results folder and
  deletes the sandboxes. This round's sandboxes are already gone, so its traces are not kept.

## Scores

Means over three runs per arm. Costs are as the eval command reports them, at API prices; the
runs used the user's claude.ai login.

| Case | Arm | Behaviour graders | Validator findings | Unknown names | Time per run | Cost per run |
|---|---|---|---|---|---|---|
| APC mini mk1 | with | 100% | 0 | 0 | ~3 min | $0.90 |
| | without | 78% | 0 | 0 | ~5½ min | $1.17 |
| UC4 mixer v3 | with | 100% | 0 | 0 | ~2½ min | $0.78 |
| | without | 93% | 0 | 0 | ~2½ min | $0.59 |
| Port v2 → v3 | with | 100% | 0 | 0 | ~3 min | $0.81 |
| | without | 100% | 0 | 0 | ~2½ min | $0.52 |

What failed without the skill:
- APC mini: in two of three runs the grid was upside down (note 0 in the top row, against the
  prompt), and two of three answers did not say that Live must be restarted to load the script.
- UC4: one of three runs assumed that the green LEDs show the mute state, which the prompt said
  is not known.

The first round hit the user's 5-hour usage limit after 7 runs; the UC4 and port cases were run
again once it had reset.

## What the scores mean

1. **With the skill, the scripts are right more often, and faster and cheaper on the
   `_Framework` case.** The gains come from the workflow: device facts read with care, the
   loading steps, and the limits of what is known.
2. **The plan's check "fewer invented names with the skill" is not met: the check found none in
   either arm.** The first version of the check had false negatives (a parameter named like an
   attribute hid it, and `start`, `stop` and `real` counted as Python's). After the fix, the 18
   scripts were checked again: still none. There are two reasons:
   - **The baseline is not Claude guessing.** Without the skill, 8 of the 9 runs read the
     installed Live's `.pyc` files themselves, four of them with their own `marshal` script (APC
     runs 2 and 3, UC4 runs 1 and 3). One run with the skill read a `.pyc` too (port, run 3). On
     a machine with Live installed, that is the honest comparison.
   - **The name check is blind to most of a v3 script.** A v3 script names its controls and
     components as text in the mappings (`"Mixer": {"volume_controls": "faders"}`), and the
     check reads only attribute names and constructor keywords. It saw 4–10 names in each v3
     script against about 30–45 in each `_Framework` script (one baseline APC run had 6), so an invented control name in a mapping
     goes unnoticed. Step 8 checks the control and element names in the mappings by class
     (Decision 43).
3. **On the v3 cases the skill costs more and adds little.** The skill v1 has no v3 references
   yet (they come with step 10), so its v3 runs spend tokens on lookups the baseline makes by
   reading files.

## The step 10 round (2026-11-18)

The same three cases, three runs per arm, against Live 12.4.16. This round had the skill's v3
references, step 8's validator rules and Decision 48's additions: the `session-ring` warning, and
two new UC4 graders, `08-session-box` and `09-value-feedback`, with the two device facts they rest
on in the prompt. The two new graders and the changed prompt mean the UC4 scores can't be compared
with the baseline's. The two arms of this round can be compared.

The login expired partway through the first attempt (`OAuth token revoked`, then `Not logged in`
for every later run). The APC case finished in that attempt, apart from one timed-out run without
the skill. Both v3 cases were run again after the user logged in again
(`iteration-2` and `iteration-2-v3` in the git-ignored workspace). The skill was the same in both.

| Case | Arm | Scripts | Behaviour graders | Validator findings | Unknown names | Time per run | Cost per run |
|---|---|---|---|---|---|---|---|
| APC mini mk1 | with | 3 of 3 | 100% | 0 | 0 | ~3 min | $0.76 |
| | without | 2 of 3 (1 timed out at 25 min) | 50% | 0.5 | 0 | ~12 min | $0.78 |
| UC4 mixer v3 | with | 3 of 3 | 100% | 0 | 0 | ~2½ min | $0.53 |
| | without | 3 of 3 | 57% | 1 | 0 | ~4 min | $0.72 |
| Port v2 → v3 | with | 3 of 3 | 100% | 0 | 0 | ~3 min | $0.71 |
| | without | 3 of 3 | 100% of the judge's, but the validator grader failed in all 3 | 1 | 0 | ~4 min | $1.07 |

What failed without the skill:
- **The session box, in every v3 script** (all six v3 runs and one APC run): each set no identity
  reply and used the framework's own session ring. That ring stays disabled until the controller
  answers an identity request, so Live draws no box. This is the UC4 load test's first bug
  (fix 1), now the validator's `session-ring` warning.
- **Values sent back for the UC4's display, in all three UC4 runs:** no element was built with
  `is_feedback_enabled=True`, so the display and the pickup get no values (the load test's
  second bug).
- **UC4:** two runs assumed the green LEDs show the mute state, which the prompt says is not
  known; one run did not use `ableton.v3`.
- **APC mini:** one grid was upside down; neither finished answer said that Live must be
  restarted to load the script; one run took almost 19 minutes, another timed out.

What the round means:
1. **The load test's lessons now reach the scripts.** With the skill, every v3 script got the
   session box and the value feedback right. Without it, none did. The skill's `tested` facts
   from the load test made that difference, and the validator would have caught the session ring
   in every script without the skill.
2. **The v3 cases are now faster and cheaper with the skill.** This reverses the baseline's
   point 3: the v3 references replace the lookups the runs without the skill made by reading files.
3. **"Fewer invented names" is still not shown: neither arm had any unknown names.** The name
   check now also sees v3 mappings (step 8). The difference between the arms shows up in
   behaviour and validator findings instead.
4. **Cost of the round:** $4.34 for the first attempt (with the failed and timed-out runs) and
   $9.10 for the v3 cases again, at API prices.

## Not covered yet

- **The trigger check** (the skill fires for Remote Script prompts and stays quiet for close
  misses): the 20 queries are written (`skills/ableton-remote-scripts/evals/trigger-eval.json`, 10
  that should fire it and 10 close misses), but not run, to stay inside the usage limit.
- **Re-runs:** done once, after step 10 (Decision 46 replaced the re-run after step 8).
