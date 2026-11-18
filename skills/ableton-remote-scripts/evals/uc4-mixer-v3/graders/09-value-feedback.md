---
type: llm
focus: trace
weight: 1
---

The faders and encoders mapped to volume and pan send Live's values back to the UC4 for its display: their elements are built with `is_feedback_enabled=True` (in `ableton.v3` the default is False), or the script sends the values in another way that works.
