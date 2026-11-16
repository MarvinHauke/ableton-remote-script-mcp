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
- **The validator reads code, it doesn't run it.**
    - Below the top level of one of Live's Python modules (`xml.etree`), names aren't checked.
      Whether a C module of Python's standard library is built into Live can't be seen, and
      whether a module counts as such depends on the Python you run the tool with; that only
      changes what is listed as not checked.
    - Mapping keys of components that answer names by pattern are not checked. That includes v3's
      `MixerComponent`, which passes `volume_controls` and the like on to its channel strips.
    - Mappings are read where the mappings function writes them as `mappings["Name"] = dict(...)`,
      as a dict literal, or in the dict it returns. Sections it builds another way are listed as
      not checked.
    - Elements are known only from the Elements class; names built in a loop or by computation
      make the element names of the mappings not checked.
    - `component-guard` follows the methods `__init__` calls one level deep.
    - Attribute names outside the mappings (`self.song().made_up()`) are not checked.
    - The framework checks need Python 3.11, the Python Live runs.
- **`log` finds a script's messages by its class name.** The framework starts each message with
  the name of the script's control surface class (as read in the decompiled 12.0 framework), so `--script` finds them only when that class is
  named like the folder. Tracebacks are found by the folder in their file paths.
- **The `Live` module is seen through a model.** Live's C++ objects are not in the compiled
  files; the index uses the Push 3 helper's pure-Python model of them, which mirrors the Live
  Object Model but is not Live itself.
