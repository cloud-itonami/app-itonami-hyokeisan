# Legacy patternless pull conversion candidate, 2026-11-02

The pinned Kotobase primary handler at commit
`d26b9374ee1a9bf9d8cad43e3b3aa9974fc9ea3b` emits a patternless pull response
containing `ok`, `graph`, `entity` and an `attrs` map of attribute names to
arrays of EDN-encoded values. Hyokeisan's old `kotoba_datomic.cljk` instead
looks for a `datoms` array. The two current source paths are incompatible;
this observation does not establish the historical live route or data state.

The staged Kotoba candidate reads one caller-supplied `attrs` response,
requires singleton values for the necessary attributes, checks type, entity,
slug and nonnegative revision, validates the sheet metadata and full grid, and
retains the **entire supplied response** as LE2 provenance in the HU1 result.
It rejects missing, malformed, inconsistent or ambiguous required values.

`check-legacy-grid.py` passed on selfhost native and Chrome 156 Wasm with a
synthetic two-sheet response, Unicode and an unknown retained attribute. It
compared every HU1 byte independently, refused wrong entity/ID, missing grid,
ambiguous title, invalid revision, unsuccessful response and datoms-only
response, and detected separate identity and response-provenance mutants in
addition to earlier controls. The staged source SHA-256 was
`5176ae78764f9cdb41765e3d49659048009a4ae1291066cba7de3b8f3a55b83e`;
compiler candidate SHA-256 was
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.

This is an unconnected parser for a caller-supplied response, not a request to
the old service. JSON/token, metadata, grid and HU1 bounds apply. A syntactically
valid response does not prove the origin, authenticated caller, visibility of
all attributes, immutable basis or completeness. No actual export, user-data
migration, QEMU, fleet synchronization or public delivery was performed.
