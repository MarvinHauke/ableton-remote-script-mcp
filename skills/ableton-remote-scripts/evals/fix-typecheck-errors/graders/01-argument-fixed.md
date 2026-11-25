---
type: llm
focus: output
weight: 1
---

In Tap_Box/components.py, every call of `_next_index` passes each parameter it has no default for (or `wrap` got a default), so the handler no longer raises a TypeError.
