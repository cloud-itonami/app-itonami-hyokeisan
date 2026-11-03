# Legacy title-keyed grid lookup candidate, 2026-11-02

The provisional Kotoba legacy-grid module now validates a bounded, complete
`sheet/gridJson` object and extracts the sparse cell frames for one requested
decoded sheet title. It validates every matrix before returning and rejects
duplicate decoded keys, missing requested names, malformed values and trailing
data. This is still a parser building block, not an exporter or import flow.

`check-legacy-grid.py` passed on Amu selfhost native and Chrome 156 Wasm with
an object containing more than 32 sheets, a Japanese title containing `!`,
missing keys, equivalent escaped duplicate keys, malformed unrelated sheets,
the earlier 1,024-column matrix and a row/column mutation control. The tested
staged source SHA-256 was
`c45d1c013f4b433e4fcd746c30d98588820f41153866d0ced30dec5bfcf31a49`;
the compiler candidate SHA-256 was
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.

The object and each matrix are bounded to 35,000 bytes and string tokens to
8,192 bytes; larger inputs refuse without truncation. These synthetic tests do
not prove all admitted bounds. In particular, matching **all** grid keys to the
sheet metadata list, authenticating and preserving a complete export and its
revision, reading a real old store, UI integration, user-data migration, QEMU
and publication remain unimplemented or unqualified.
