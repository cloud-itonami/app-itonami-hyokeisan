# Legacy browser import candidate, 2026-11-02

The local Hyokeisan candidate accepts a user-provided title and separate
`sheetsJson` and `gridJson` files, converts them in Kotoba/Amu Wasm, and
requires confirmation after preview. The UI says that only part of the first
sheet is shown, unsupported attributes are retained as source text, and that
the user must verify that the files came from the same revision. The host
performs no remote request. Before committing it checks the preview's original
local state, obtains the existing storage lock, and writes a recovery copy.

`check-legacy-import-browser.py` passed in synthetic local Chrome for missing
sheet refusal; preview and cancel; failures writing the recovery copy and
current state; stale-storage refusal; byte-exact HU1 conversion including
source provenance; second-sheet navigation and reload; and loopback-only
requests. The exact candidate also passed the existing workbook browser,
1,024-cell/SUM, synthetic IME, session-draft and unload-warning regressions.
The first HS1 regression attempt expected an injected 1 ms hidden-tab timer to
fail, but the edit saved successfully instead; this timer-only injection was
race-dependent. The test was changed to withhold the step Worker response as
well as shortening the timer; the full HS1 regression then passed on the same
final build. This synthetic control does not
explain the previously observed natural Worker timeout.
The candidate Wasm SHA-256 was
`614714d14ac8093955252348e8d2f80bf30d1a1c4a9460c7d4334aec91f27a2c`,
staged source SHA-256 was
`80a0c5447e689c368637404478aa64066e7b0ccfb883c7e6f59dea8ededded05`,
and compiler candidate SHA-256 was
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.

The files' origin, identity, revision and completeness cannot be verified by
this flow. It does not obtain an old-store export and no actual user data was
migrated. Size and supported-format limits refuse inputs rather than truncate;
behavior at every admitted limit, other browsers, physical IME, crash durability,
the previously observed natural Worker timeout, QEMU, fleet and public delivery
remain unqualified.
