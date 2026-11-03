# Hyokeisan workbook browser candidate — 2026-11-02

The browser candidate now stages the Kotoba sheet, workbook, HS1 migration and
workbook UI modules into one selfhost compiler unit. Existing HS1 storage stays
readable. The user may explicitly preview and confirm migration to provisional
HU1 view state containing the whole HW3 workbook and the original HS1; the
prior snapshot is copied locally before the current key is replaced. The same
physical localStorage key is retained so the old HS1-only candidate refuses the
new state instead of initializing over it.

The Kotoba view supports adding and switching sheets, navigating in 4×4 pages,
editing cells, and saving the entire workbook. A1:D4 calculations use the
existing bounded integer formula subset; formula cells on other pages are
marked uncalculated. The browser host retains its lock, explicit backup preview,
prior-state recovery, retry, per-tab session draft and digest checks. The
canonical broker is copied from the pinned source and declares no operations.

Synthetic Chrome 156 loopback checks passed:

- HS1 conversion preview/cancel/confirm; backup-write and primary-write failure;
  stale-upgrade and stale-tab refusal; original data retained and recoverable.
- Multiple sheets, E1/H8 editing, reload, HU1 backup export and import
  preview/cancel/confirmation, malformed refusal, old-app refusal, HS1 restore
  and recovery of the previous workbook.
- An independently framed 1,024-cell sheet and a second sheet: editing A1 and
  AA50, navigation and reload; the rest of the workbook and provenance matched
  the expected bytes. A row-coordinate mutation was rejected by that check.
- Existing HS1 browser regression and separate HU1/HS1 synthetic IME,
  same-tab journal and unload-warning checks. These do not qualify a real OS
  IME, crash, closed-tab or power-loss recovery.

The measured candidate was compiled by the Amu selfhost image SHA-256
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.
Staged program SHA-256:
`155832c410ad29dece46a90f0dd06421ef9a4878a8fbbb9cd5755aa540f58fa8`.
Wasm SHA-256:
`d0ea242fbf9282f8f531766269bfe7c1add20f93dcabd427f399ee352544a9b7`.
The build uses the exact canonical broker revision and digest in its pin.

Reproduce using `scripts/build-browser.py`, `scripts/check-workbook-browser.py`,
`scripts/check-workbook-large.py` and the existing browser regression scripts;
set `HYOKEISAN_TEST_WORKBOOK=1` for their HU1-specific checks. Test inputs and
user choices are synthetic. The earlier natural hidden-tab Worker timeout is
not resolved by these runs. The 35,000-byte local snapshot bound, limited
formula semantics, maximum-input resource behavior, real old-origin export and
migration, physical IME, other browsers, CID/public delivery, QEMU and release
remain unqualified. No production service was changed.
