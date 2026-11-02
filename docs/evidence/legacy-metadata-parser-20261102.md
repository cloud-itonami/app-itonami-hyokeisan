# Legacy sheet metadata parser candidate, 2026-11-02

The staged Kotoba migration building block parses the old `sheet/sheetsJson`
array one object at a time, returning ordered, length-framed sheet ID/title
pairs. Numeric and string IDs have distinct `n:` and `s:` prefixes. Duplicate
IDs or titles, malformed JSON, missing required fields and unsupported ID
forms are refused. A separate projection produces the framed title sequence
used by `legacy-grid-match-titles`; the full source metadata must be retained
by any future importer to preserve other fields.

`check-legacy-grid.py` passed on Amu selfhost native and Chrome 156 Wasm for
41 metadata objects, numeric/string IDs, title extraction and matching against
the grid, duplicate IDs and names, malformed fields and trailing data. It also
detected independent coordinate, title-count and duplicate-ID mutants. The
staged source SHA-256 was
`bda1452e5c2899e95508db52a3a7df3853bf85bb1889c702cd8cb9b0e4e8d162`;
compiler candidate SHA-256 was
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.

The parser refuses metadata over 35,000 bytes, more than 1,024 sheets, IDs
outside its supported forms, and individual objects exceeding the JSON
validator's bounded object, array, nesting or string-token limits. The outer
sheet array is not limited to 32. Tests do not establish behavior at every
admitted bound. This module is staged by the test and not yet in the browser
builder or UI. A complete export must bind identity, revision, metadata and
grid and retain the original bytes. Actual old-store access, import/save,
QEMU, fleet and public delivery remain unqualified. The generic JSON validator
is adapted from Bunsho commit `09f425164e2af3985a12fa661970673ac70e16d6`.
