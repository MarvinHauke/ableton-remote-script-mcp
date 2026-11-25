---
type: llm
focus: output
weight: 1
---

`jump_button = ButtonControl()` and its handler `@jump_button.pressed` over `def jump_button` are still there (not renamed or removed), and the decorator line carries `# pyright: ignore[reportGeneralTypeIssues]`.
