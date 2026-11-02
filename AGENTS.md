# itonami Hyokeisan（表計算） — 旧 etzhayyim-project-sheets — Google Sheets v4 + Microsoft Graph (workbook) compatible spreadsheet API

> 2026-10-31（JUN-700）: Cloudflare Worker の edge facade は退役した。ブラウザ側は静的配信（`appview/README.md`）。
> 下の edge 構成図とホストは旧構成の記録で、itonami.app 上には存在しない。

**kazu.itonami.app** — a spreadsheet API whose external surface is shaped like **both**
Google Sheets v4 and Microsoft Graph workbook, over **one** canonical store on **kotoba
datomic** (graph `sheets-v1`). Third vertical of the workspace-compat program.

SSoT: `90-docs/adr/2606010500-workspace-compat-datomic-schema.md`

## 一行定義

Sheets ≝ CanonicalSpreadsheet[:sheet/*, gridJson] × KotobaDatomic[sheets-v1] × {GoogleSkin[/v4/spreadsheets], MicrosoftSkin[/v1.0/me/drive/.../workbook]}

## アーキテクチャ

```
Google SDK  → kazu.itonami.app/v4/spreadsheets/{id}/values/{range}                  ┐
MS Graph SDK→ kazu.itonami.app/v1.0/me/drive/items/{id}/workbook/worksheets/{s}/range ┘
  CF Worker sheets-compat (50-infra/cloudflare/workers/sheets-compat)
   ├─ /xrpc/app.itonami.kazu.*  → pod (actor-worker passthrough)
   └─ provider REST → canonical XRPC → pod → reshape to provider JSON
  lg-sheets pod (lg, FastAPI server.py)
   → kotoba datomic transact/q/pull on graph sheets-v1 (:sheet/* namespace)
```

Same edge/routing/persistence rules as calendar/drive (ADR-2605111200; atproto
catch-all actor:true → pipethroughActorWorker → kazu.itonami.app/xrpc → `SHEETS_POD_URL`
tunnel → pod; dedicated graph `sheets-v1`).

## Canonical XRPC methods (app.itonami.kazu.*)

| method | Google Sheets v4 | Microsoft Graph workbook |
|---|---|---|
| `spreadsheetsGet` | spreadsheets.get | GET …/workbook/worksheets |
| `spreadsheetsCreate` | spreadsheets.create | POST /me/drive/root/children |
| `valuesGet` | spreadsheets.values.get | GET …/range(address='…') |
| `valuesUpdate` | spreadsheets.values.update (PUT) | PATCH …/range(address='…') |
| `valuesBatchUpdate` | spreadsheets.values:batchUpdate | (workbook session batch) |

Lexicons: `00-contracts/lexicons/app/itonami/kazu/`. **Storage model (ADR D6)**: one
spreadsheet = one datomic entity; worksheet metadata in `:sheet/sheetsJson`, cell values in
`:sheet/gridJson` = `{title: [[stringified cells]]}` (no-float rule — cells are strings, cast
at the edge per valueRenderOption). A1 notation parsing in `lg_sheets/a1.py`. ETag/If-Match ←
`:sheet/revision`.

## Edge specifics
- MS function-form `range(address='Sheet1!A1:C10')` is normalized to `/range?address=…` by a
  pre-router middleware in `sheets-compat/src/index.ts`.
- Google `values:batchUpdate` (colon path) matched via a Hono regex param.

## ファイル構成
```
lg/  (bb.edn, run_tests.clj)
└── src/sheets/{server,handlers,store,mapping,a1,kotoba_datomic,edn_tx,ids}.cljc + graphs/health.cljc
test/sheets/{handlers,gitoffice_normalize}_test.cljc   # 13 tests / 43 assertions
(edge) 50-infra/cloudflare/workers/sheets-compat/  # Google + MS skins (12 tests)
(infra) 50-infra/vultr/lg-sheets-pool/             # Helm (mirror lg-drive-pool)
```

## Test
```bash
cd lg && kbb run_tests.cljk
cd 50-infra/cloudflare/workers/sheets-compat && node --test test/*.test.ts
```

## Clojure port (ADR-2606280030, langgraph-python → langgraph-clj)

`lg/src/sheets/*.cljc` is the **clj/bb twin** of `lg_sheets/*.py` (faithful: same XRPC
endpoints, same `:sheet/*` datom mapping, same A1/grid/revision behavior, same sparse
GitOffice round-trip). The `health` graph is now a **langgraph-clj StateGraph**
(`sheets.graphs.health`, START→probe→END); `httpx`→`babashka.http-client`,
JSON→`cheshire`, FastAPI→`org.httpkit.server` (`sheets.server`). Map keys stay strings
(JSON wire shape). Stores are synchronous (the Python `async` is dropped).

```bash
cd lg && kbb run_tests.cljk   # clj twin: 13 tests / 43 assertions
bb run -m sheets.server                                       # or `kbb -M:serve` (org.httpkit on :PORT)
```

**Canonical (ADR-2606280030):** the `lg/src/sheets/*.cljc` twin is now the **canonical
code** for the lg-sheets pod. The DEV-stage Python (`lg_sheets/*.py` + `tests/test_*.py` +
`pyproject.toml` + `langgraph.json` + `Dockerfile`) was DELETED once the clj twin existed
(founder directive "twin の py を削除"). The twin is a full 1:1 cover of every former `.py`
module — no native dep forced any `.py` to be kept. Nothing outside this app dir imported
`lg_sheets`. This was a deletion (not a deploy cutover): re-wiring `langgraph.json`/
`Dockerfile` at the clj server is the separate follow-up that adds clj deploy scaffolding.
