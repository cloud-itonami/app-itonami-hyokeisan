# Itonami Hyokeisan（表計算）

Hyokeisan is the planned Itonami spreadsheet dapp. Its model and UI are
intended to be written in Kotoba and built by Amu selfhost for the user's
browser and Itonami OS. Browser execution targets Wasm; QEMU is used to qualify
the OS host. The workbook, formula engine, UI and durable storage are not yet
implemented or released.

The [shared office dapps design](https://github.com/cloud-itonami/app-itonami-bunsho/blob/2fd57da398b9e3ae7e817994a190b1c9f860dc38/docs/office-dapps-spec.md)
covers the app/host boundary, state and migration, consent, and release gates.
The link is pinned to the design proposal in the open Bunsho draft PR;
[JUN-704](https://linear.app/kotobalabs/issue/JUN-704) tracks Hyokeisan.

The experimental [integer grid](src/hyokeisan/grid.kotoba) and
[snapshot-value evidence](docs/evidence/grid-snapshot-20261102.md) cover a
bounded core, not a complete workbook or persistent storage. The candidate
`hyokeisan.itonami.app` is not a claim of an available or deployed service.
