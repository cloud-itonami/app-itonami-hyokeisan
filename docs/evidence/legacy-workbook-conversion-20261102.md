# Legacy workbook conversion candidate, 2026-11-02

The staged Kotoba converter accepts a caller-provided title, legacy sheet
metadata JSON, and legacy title-keyed grid JSON. It validates both structures
and their complete title sets, builds a HU1 candidate in metadata order, and
keeps the exact three supplied values in an `LE1` frame inside HW3 provenance.
It rejects empty sheet lists, invalid or mismatched parts, and results that
exceed the existing 35,000-byte HU1 limit. It does not read a store or write
browser storage.

`check-legacy-grid.py` passed on Amu selfhost native and Chrome 156 Wasm for
two sheets with reordered grid keys, Unicode, blanks and formula text. The
complete HU1 bytes, including provenance, matched an independent fixture and
the resulting state passed `ui-read`. Missing sheets, empty metadata and a
synthetic candidate exceeding the storage limit were refused. Independent
coordinate, title-count, duplicate-ID and omitted-grid-provenance mutants
were detected. The staged source SHA-256 was
`cd589e759d9a29ee6f480c9e23d9fe71edf19b96d1aacd176f7dd11ba66346d6`;
compiler candidate SHA-256 was
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.

The three inputs are caller-supplied: their identity, revision, completeness
and origin are not authenticated by this converter. Provenance retains the
supplied values, not an entire independently verified old-store export. This
test stages the modules separately from the browser builder; preview,
confirmation, backup/rollback, actual user migration, QEMU, fleet and public
delivery are not established. Earlier parser bounds and limitations apply.
