# Wide legacy pull import, 2026-11-02

An independently framed synthetic workbook with a 1,024-column row fits the
existing HU1 storage bound. The two-file import succeeded, but the same grid
inside a pull response exceeded the earlier 8,192-byte escaped-string token
limit. Raising that limit alone was insufficient: a direct Chrome Wasm probe
trapped with `budget/bytes :arena :string-pool` while the native probe returned
the expected result. The attempted browser import reported refusal; that failed
probe exited before independently checking storage. The original probes remain
in the task workspace.

The Kotoba JSON string decoder now splits at complete UTF-8 and escape
boundaries, decodes bounded leaves, and combines them as a balanced tree.
The JSON document and token bound is 35,000 bytes; the separate legacy cell
scanner still has its own 8,192-byte token bound. On the resulting browser
candidate, the synthetic 1,024-column two-file and pull imports both passed;
all HU1 cell and provenance bytes matched independent fixtures. The normal
import, workbook, large-sheet and HS1 browser regressions also passed.
Native and Chrome Wasm parser tests passed long escaped Unicode and malformed
string cases; a negative control that split a surrogate pair was detected.

Candidate Wasm SHA-256:
`d96a753fdca633857b91f4fc71ca137baa93690c43d0b4285a1e870ec66db672`;
staged source SHA-256:
`7861fe4f515a2114d41733db22cb682ba0ab2d5c36945e25dd5d8b711de2b773`;
compiler candidate SHA-256:
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.
These are synthetic local results, not proof for every admitted input, a
verified old export or user migration. QEMU, fleet and public delivery remain
unqualified.
