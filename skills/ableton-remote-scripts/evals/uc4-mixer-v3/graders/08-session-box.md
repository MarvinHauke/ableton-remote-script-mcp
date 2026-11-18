---
type: llm
focus: trace
weight: 1
---

The script makes Live draw the session box of 8 tracks without counting on an identity reply from the UC4 (the prompt says it is not known): for example a session ring class of the script's own that enables itself, set as the Specification's `session_ring_component_type`. A script that leaves the framework's ring and sets no identity reply fails, because the framework enables that ring only after the controller is identified. A script that sets `identity_response_id_bytes` it made up fails too.
