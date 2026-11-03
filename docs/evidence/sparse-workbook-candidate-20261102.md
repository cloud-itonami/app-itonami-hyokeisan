# Sparse workbook candidate — 2026-11-02

`src/hyokeisan/workbook.kotoba` is an unconnected Kotoba candidate for a
multi-sheet, sparse, byte-framed workbook. It retains title, sheet identifiers,
sheet titles, raw cell text and an exact source-provenance string; it validates
canonical framing, coordinate bounds, cell ordering and duplicate identifiers.
One-based row/column coordinates can represent cells outside the existing 4×4
editor. There is no legacy-format parser, UI integration, browser persistence
adapter or OS adapter in this unit. `HW3` is a provisional candidate, not a
published or cross-version compatibility contract.

Amu native and Chrome 156.0.8078.74 Wasm passed synthetic multi-sheet tests,
including metadata retention, duplicate-sheet/cell negative controls, 256
incremental additions in one invocation, and an addition/readback on a
prebuilt 1,024-cell workbook. The Wasm tests used 25,000,000 fuel. The 256
case consumed 5,031,218; the prebuilt 1,024 case consumed 336,795. These cases
do not establish performance or resource safety for all inputs within the
provisional bounds. Compiler SHA-256:
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.
Source SHA-256:
`429568d88650f556032708ba4f45983552adacfa41e22c18ad0846327e0b6c76`.

An earlier flat-document-vector design trapped when a vector exceeded its
32-element runtime limit. A subsequent framed prototype trapped with
`vector-table-exhausted` during 256 incremental inserts even with fuel
remaining. Encoding frame positions as integers alone did not remove the
trap; reading numeric coordinates from the original bytes without creating
substrings allowed the 256-insert fixture to pass. These observations do not
prove the arena cannot be exhausted by larger or adversarial input. The UI
must refuse or retain prior state on a guest trap, and the supported limits
must be qualified before any import or release.

Reproduce with `python3 scripts/check-workbook-wasm.py AMU_DIR OUTPUT_DIR CHROME`.
All fixtures are synthetic. Actual migration, spreadsheet semantics, browser
persistence, QEMU, fleet synchronization and publication remain unqualified.
