# Known limits

- **macOS only.** Live installs are looked for as app bundles in `/Applications`; Windows is not
  supported.
- **Only Live's own scripts are indexed.** `outline` works on the Remote Scripts that ship with
  Live, not on scripts in your User Library.
- **Every fact is `observed`.** Nothing has been checked yet by loading a script in Live, and no
  secondary source is compared.
- **Signatures are as complete as the compiled files.** Default values that the compiled files
  don't keep are missing.
- **Outlines read code, they don't run it.**
    - A call under a condition is shown as conditional unless the script's own class attributes
      decide the test; then it is marked as built or not built.
    - Elements made by helper functions are followed three calls deep.
    - Scripts that build their controls from tables of data, that send raw MIDI themselves, or
      that build their Specification in a function show few or no elements.
- **The `Live` module is seen through a model.** Live's C++ objects are not in the compiled
  files; the index uses the Push 3 helper's pure-Python model of them, which mirrors the Live
  Object Model but is not Live itself.
