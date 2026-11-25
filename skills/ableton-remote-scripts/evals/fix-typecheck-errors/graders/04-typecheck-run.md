---
type: llm
focus: trace
weight: 1
---

The skill's `typecheck.sh` (basedpyright or pyright with the project's stubs) ran on Tap_Box, and its last run reported 0 errors. If it said there were no stubs, the agent asked the user to build them with `build-stubs --project`, gave a reason, and did not build them itself.
