# Workbook formula candidate, 2026-11-02

JUN-704 extends the provisional HU1 browser candidate to evaluate a bounded
integer formula subset against the active sparse sheet, including cells outside
the visible page. It supports single references or signed integers, one `+`,
`-`, or `*`, and rectangular `SUM`. Cycles, invalid syntax, arithmetic outside
the bounded range, excessive reference depth and resource refusals produce an
error. `SUM` scans at most 4,096 stored cells on the sheet; references are
bounded to 32 formula evaluations. This is not general spreadsheet compatibility.

The selfhost compiler candidate (SHA-256
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`)
produced browser Wasm SHA-256
`7cf8da6878e0651c715301940fd958e721a0f00058efd8979684ad867165eaec`;
the staged source SHA-256 was
`dd712539f6bf5e5cfb5fe61c16e58f6f78238d3395e378b3e4db26c7bd64bdd2`.
The candidate uses canonical broker revision `e00ae75e1c589f76b4f53a88a5e3256c98c9e162`.

- `check-workbook-formula.py`: native and Chrome Wasm model cases passed,
  including off-page references, sheet isolation, a 64-cell sum, cycles,
  coordinate boundaries, malformed expressions, and a column mutation control.
- `check-workbook-browser.py`: synthetic Chrome loopback upgrade, editing,
  off-page dependency recalculation, save/reload, stale state and rollback passed.
- `check-workbook-large.py`: a 1,024-cell sheet plus a second sheet was preserved
  while editing and evaluating an off-page reference. This is not a 1,024-cell
  SUM stress test or proof of behavior at all admitted resource bounds.
- `check-browser-ui.py` passed the HS1 regression. HU1 synthetic Chrome IME,
  session-draft and unload-warning checks passed.

These are local synthetic tests. Physical IME, crash durability, other browsers,
real user migration, Itonami OS/QEMU, fleet trust and synchronization, external
delivery and publication remain unqualified. A previously observed natural
hidden-tab Worker timeout remains unresolved. Amu PR #1779 is a dependency and
was still in the merge queue when this candidate was tested.
