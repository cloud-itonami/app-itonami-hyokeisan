# HS1 to sparse workbook conversion — 2026-11-02

`hs1-to-workbook` converts the 16 cells of a valid candidate HS1 snapshot to
one sheet in the provisional HW3 sparse workbook, with the same one-based
row/column positions and the exact HS1 string retained as provenance. Empty
cells remain represented. Invalid input returns none. This is a conversion
kernel only: the existing editor is still HS1-only and no storage migration,
old-origin fetch, user-data import, QEMU run or release occurred.

The staged source modules passed native Amu and Chrome 156.0.8078.74 Wasm
with 25,000,000 fuel. Synthetic input covered all 16 coordinates, Unicode,
newline, an empty cell, a 128-byte cell and a formula. The exact original was
recovered from HW3. A transposed-coordinate mutation returned the expected
failure, and malformed/trailing/non-ASCII-prefix data was refused. The source
graph is staged into one compiler unit; project-linker qualification is not
implied. Compiler SHA-256:
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.
Conversion source SHA-256:
`bafa0646863a46f9ac4a03f861518f9787fc90cd12cd8e6fc7959a33d3edf1f1`.

A separate synthetic Chrome loopback test placed a valid HW3 into the existing
HS1-only app's storage. On two reloads the app refused to open it, exposed no
editable grid, and retained the exact saved bytes. This protects against that
specific rollback; it does not qualify an actual upgrade, atomicity, crash
recovery, older deployments or a real migration.

Reproduce with `scripts/check-hs1-migration.py`, `scripts/build-browser.py`
and `scripts/check-browser-ui.py` using the documented arguments and pinned
selfhost compiler and broker.
