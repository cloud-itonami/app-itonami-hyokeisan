# Legacy grid matrix parser candidate, 2026-11-02

The old `lg/src/sheets/mapping.cljk` and `handlers.cljk` at default-branch
commit `2264a70082713b3f3f17d73e96783489d151b929` store a sheet's grid as a
JSON matrix of strings inside the title-keyed `sheet/gridJson` object. The
new Kotoba parser accepts **one matrix**, validates the complete input, and
emits row-major sparse HW3 cell frames. Empty cells contribute no record;
the caller must retain the original matrix and metadata. It does not discover
or read the old store, validate a complete export, or alter storage.

`check-legacy-grid.py` passed with the Amu selfhost native runner and Chrome
156 Wasm, including a synthetic 1,024-column row, 70 further rows, Japanese,
emoji, escaped Unicode and control characters, malformed JSON and a
row/column-swapped negative control. The test compares all emitted frames to
an independently constructed expected byte string. Staged source SHA-256 was
`798d5a4f2980bc023f3935d26caf017d22dd6c4525d4e89a7f9c27a1aba8cd2e`;
compiler candidate SHA-256 was
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.

The parser refuses matrices over 35,000 bytes and individual JSON string
tokens over 8,192 bytes; it does not truncate them. Those limits and runtime
behavior are not qualified for all possible inputs. Object parsing, sheet
identity, revision consistency, missing or corrupt grid detection, preservation
of the full raw export, UI integration, actual user-data migration, QEMU and
publication remain open. The JSON string decoder is adapted from Bunsho at
commit `09f425164e2af3985a12fa661970673ac70e16d6`.
