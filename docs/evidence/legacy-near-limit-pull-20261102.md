# Near-limit pull import, 2026-11-02

The existing Kotoba/Wasm browser candidate was tested with a synthetic
patternless pull response containing a single 1,600-column row. Its expected
HU1 state, including the exact original response, is 34,518 UTF-8 bytes. The
Chrome loopback test previewed and committed the import and compared every
stored byte to an independently constructed fixture. A subsequent 1,700-column
fixture would produce more than the 35,000-byte storage limit; it was refused
and the prior 34,518-byte state remained unchanged.

The same run passed the earlier synthetic 1,024-column two-file and pull cases,
invalid identity, backup and write failure, stale-state and reload checks. It
used the build with Wasm SHA-256
`d96a753fdca633857b91f4fc71ca137baa93690c43d0b4285a1e870ec66db672`
and compiler candidate SHA-256
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.

This is one synthetic data shape, not a guarantee for all inputs under the
limit or for real export completeness, origin, authorization or revision. No
actual user data was accessed. QEMU, fleet and public delivery remain open.
