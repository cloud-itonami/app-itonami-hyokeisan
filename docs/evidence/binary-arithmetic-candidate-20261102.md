# Hyokeisan binary arithmetic candidate — 2026-11-02

The Kotoba 4×4 candidate accepts one binary subtraction or multiplication of
signed integer literals and/or cell references. Results outside ±1,000,000,000,
cycles, malformed expressions and unsupported compound expressions display
`#ERROR`. This is a bounded integer subset, not Excel formula compatibility.
The existing HS1 snapshot format is unchanged.

Native Amu and Chrome 156.0.8078.74 Wasm returned the expected result for the
model, and independent mutations of addition, subtraction and multiplication
were rejected by the checks. Cases include signed operands, a cycle,
out-of-bounds multiplication, a compound expression and a non-ASCII invalid
formula. Model source SHA-256:
`bd86c24983b7c4b37449113ade12990d8cdd144ce6ffd443cd57fefea69cd014`.
Compiler SHA-256:
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.
The standalone model Wasm test uses the Amu harness without a fuel limit.

A separate selfhost browser candidate (program Wasm SHA-256
`10085ce796a8a768fc8b97311fe526dee318555bda548ac1ebd322043864f82e`)
passed the synthetic Chrome loopback UI suite, including entering both new
operators, recalculation and save/reload, the existing backup and refusal
checks. An earlier superseded UI test was interrupted manually; it is not a
pass. These checks do not establish physical IME, other browsers, QEMU, legacy
migration, public delivery or release readiness.

Reproduce with `scripts/check-sheet-wasm.py`, `scripts/build-browser.py` and
`scripts/check-browser-ui.py` using their documented arguments and a local
Amu selfhost root, the pinned broker repository and Chrome.
