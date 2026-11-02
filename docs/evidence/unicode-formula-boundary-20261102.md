# Hyokeisan UTF-8 formula boundary — 2026-11-02

The candidate accepts a cell containing unsupported Unicode formula text and
shows `#ERROR`; it preserves the exact input in HS1 on save and reload. Plain
Unicode text cells remain supported. The formula grammar itself is still the
bounded ASCII integer subset; this is not Unicode formula support.

Before the fix, the exact sheet source at `35c3b303d9451cfd83cd4dd732f2abf599c75a34`
with test entries for `=ああ1234` or `=é` terminated native Amu with exit 133.
The corresponding separately compiled browser Wasm runs each reported
`:status :trap`, exit 120, with `KEXE_TRAP` / `SIGILL`. The first diagnostic
script initially expected the host-specific `wasmTrap` field and failed its
assertion even though the guest report proved a trap; the second checked the
report field instead. This distinction is kept here rather than treating that
first diagnostic command as a successful test.

The fixed Kotoba model (source SHA-256
`59af185c14ef0810b34abb5b7f8d540dc8d65ce8551cd4475d772c173f78be38`)
passed native and Chrome 156.0.8078.74 Wasm with those inputs and existing
addition, subtraction and multiplication mutants. Compiler SHA-256:
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.
The standalone Wasm harness was unmetered. The separate browser app build's
Wasm SHA-256 was
`328229406273e7a7e05ce8d9b09b73c48729f2c2cfd36c1a17b2f8f6e28127c1`.

The first full Chrome loopback UI run saved and reloaded the two Unicode cases
but later failed when a hidden first tab's Worker timed out during a two-tab
check. A second run passed after the test foregrounded the tab it operated and
waited for the preceding restore to finish. It also retains the existing
synthetically injected hidden-tab timeout/retry check. The foreground run does
not explain or resolve the natural timeout; it remains open. This is synthetic
Chrome evidence, not real OS IME, other browser, QEMU, migration, gateway or
release qualification.

Reproduce via `scripts/check-sheet-wasm.py`, `scripts/build-browser.py`, and
`scripts/check-browser-ui.py` with their documented arguments, the pinned
Amu selfhost candidate, canonical broker repository and Chrome.
