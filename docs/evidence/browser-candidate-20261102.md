# Hyokeisan browser candidate — 2026-11-02

This is a bounded, local-only candidate, not a complete workbook or release.
The Kotoba model contains one 4×4 sheet with 16 text inputs of at most 128
UTF-8 bytes. Formula support is intentionally explicit: signed integers up to
six digits, `=A1` references, one `+` expression such as `=A1+B1`, and
`=SUM(A1:B2)` over an ordered range. Referenced nonnumeric data, unsupported
syntax, out-of-range arithmetic and cyclic references display `#ERROR`.
Formula results are bounded to ±1,000,000,000. This does not implement general
spreadsheet syntax, functions, floating point, multiple sheets or OOXML.

A versioned `HS1|` length-framed snapshot stores exactly 16 cells and rejects
malformed, trailing or oversized input. The browser candidate uses the same
local Worker protocol and a DOM/storage adapter, Web Locks to refuse stale
cross-tab writes, the pinned shared broker, and no declared external operations.
It uses a distinct candidate localStorage key, so no old-origin migration is
assumed. This new text/formula model does not yet reuse the earlier integer-grid
kernel; their integration and any migration between their state representations
remain open.

On macOS ARM64 / Chrome 156.0.8078.74, native Amu and browser Wasm ran the
model test successfully. Replacing addition with subtraction made both report
the expected test failure. A loopback Chrome UI test exercised grid editing,
reference addition, SUM, recalculation after input changes, cyclic reference
errors, save/reload, oversized input refusal, concurrent-tab refusal, simulated
storage failure, corrupt saved input refusal and mutated artifact digest refusal.
Observed main-page requests were loopback only.

Compiler image SHA-256:
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.
Model source SHA-256:
`8168e4fdc603355622b3e9eb762cb2db6332f4e8d20d72e8a90733dc57c7c689`.
Browser Wasm SHA-256:
`2cdba4135f4104396785dc9e34cb90c060dd5f1bf0966c2894131ccc21d7bbbc`.
Broker revision `e00ae75e1c589f76b4f53a88a5e3256c98c9e162`, SHA-256
`7f760128c3a58098123c31ec3dd34b9c871932e3933f2c952facc4ab0e647212`.
Amu compiler is the unmerged candidate in kotoba-lang/amu#1779. The digest
is generated with the candidate bundle and is not independent release evidence.

Reproduce using `scripts/check-sheet-wasm.py AMU_DIR NEW_OUTPUT CHROME`,
`scripts/build-browser.py AMU_DIR BROKER_REPO NEW_BUILD`, then
`scripts/check-browser-ui.py AMU_DIR NEW_BUILD NEW_OUTPUT CHROME`.
Cross-browser, accessibility, worst-case calculation/performance, interruption
and crash recovery, actual old data migration, Itonami OS/QEMU, fleet,
distribution and production qualification remain open.
