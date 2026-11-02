# Pull preview identity fields, 2026-11-02

After Kotoba validates and converts a user-selected pull response, a separate
bounded Kotoba operation extracts its graph, entity and revision. The browser
decodes the framed result and shows these values as text in the confirmation
dialog, alongside the existing warning that source and visibility cannot be
authenticated. This lets the user compare the displayed fields with their own
records; it is not an origin, authorization, basis or completeness proof.

Synthetic Chrome loopback tests checked the expected graph, entity and revision,
an HTML-looking graph value rendered as text, failed identity, cancellation,
storage failures, stale state, exact provenance, reload, a 34,518-byte state
and over-limit refusal. Native and Chrome Wasm model checks passed. The HS1
and workbook regressions passed on a build differing from the final build only
in `style.css`; the final build passed the full legacy-import test. Wasm SHA-256:
`0681eb47e1f1b0326760976ca9c571e614483bbf18a52178f82cd9224f29da64`;
staged source SHA-256:
`4ab8a06e5f6483a8b5946340ad5537be490fbeebe6901b9cf1f3db4cc173eef3`.

No live old-store request or real user migration occurred. Other browsers,
physical IME, crash durability, QEMU, fleet synchronization and public delivery
remain unqualified. The earlier natural Worker timeout remains unresolved.
