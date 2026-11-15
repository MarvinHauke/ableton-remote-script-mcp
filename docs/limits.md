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
- **The validator checks the basics only.** It checks folder names, syntax, `create_instance` and
  imports. Below the top level of one of Live's Python modules (`xml.etree`), names aren't
  checked, and whether a C module of Python's standard library is built into Live can't be seen.
  Whether a standard library module counts as built in or as such a C module depends on the
  Python you run the tool with; that only changes what is listed as not checked.
- **`log` finds a script's messages by its class name.** The framework starts each message with
  the name of the script's control surface class (as read in the decompiled 12.0 framework), so `--script` finds them only when that class is
  named like the folder. Tracebacks are found by the folder in their file paths.
- **The `Live` module is seen through a model.** Live's C++ objects are not in the compiled
  files; the index uses the Push 3 helper's pure-Python model of them, which mirrors the Live
  Object Model but is not Live itself.
