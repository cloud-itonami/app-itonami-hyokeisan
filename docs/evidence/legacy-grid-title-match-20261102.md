# Legacy grid and title-set matching candidate, 2026-11-02

The Kotoba legacy-grid building block can now compare all decoded grid object
keys against a caller-supplied sequence of length-framed sheet titles. It
validates the grid and every matrix, rejects duplicate keys and duplicate
titles, and requires both membership and cardinality to match. An empty grid
matches an empty title sequence. Order does not affect the match.

`check-legacy-grid.py` passed on Amu selfhost native and Chrome 156 Wasm with
41 synthetic sheet names, reversed order, missing and extra titles, duplicates,
malformed title frames and corrupt matrix values. Row/column transposition and
removing the cardinality check were each detected by separate mutant controls.
The staged source SHA-256 was
`92599b89c6f5dfae6c717583d919ce6f3775619dcfc4863d5609669817738d02`;
compiler candidate SHA-256 was
`2c551579c06a0228029bb06bae177e93126ecbbc37d636d693c471dbac8d1536`.

This function does not parse old sheet metadata or establish that the caller's
title sequence came from the same revision as the grid. It does not import or
persist a workbook. The 35,000-byte object and title-input bounds and the
8,192-byte JSON string-token bound remain refusals, and behavior at all admitted
resource limits is not established. Real export provenance, migration, QEMU,
fleet and public delivery remain open.
