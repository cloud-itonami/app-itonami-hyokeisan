# Local pull-response import candidate, 2026-11-02

The browser candidate accepts a user-selected patternless Kotobase pull JSON
file and invokes the Kotoba/Amu Wasm converter. It previews the first sheet
before explicit confirmation, warns that provenance and permission-filtered
omissions cannot be verified, and retains the entire supplied response in LE2
provenance. The app makes no service request on this path.

The synthetic Chrome loopback test passed for invalid identity refusal;
preview/cancel; recovery-copy and current-write failures; stale-storage
refusal; byte-exact conversion and source retention; reload; and a request
allowlist limited to loopback. The existing two-file import and workbook/HS1,
1,024-cell, synthetic IME, session-draft and unload-warning regressions also
passed on the same build. Candidate Wasm SHA-256:
`8ad4886c771285afd6e62e675f21c26c50140b80c6a8093e71b986f30c9b52ba`;
staged source SHA-256:
`5c64224809d5290afc2b4419fe6afc06101dcd9ec905e774e49344b905a28118`;
compiler SHA-256:
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.

The response is supplied by the user; its origin, authentication, visibility,
basis and completeness are not established by this test or the app. No old
service was accessed and no actual user data was migrated. Input and output
bounds apply. Other browsers, physical IME, crash durability, prior natural
Worker timeouts, QEMU, fleet synchronization and public delivery remain open.
