# SUNJACK-ERP Product Optimization Phase 2D — PCR-008

## Scope and result

PCR-008 adds read-only, live inventory reference to the shared Quote editor for new Quotes, Customer and FollowUp related creation, and Quote revisions. It does not reserve or commit inventory and does not change Quote or order permissions. No migration was added.

The user-provided starting point was `master` at `4b603a84f3141e5da507d326360a440c3f6746f3`; CI #136 was reported green for `backend`, `backend-postgres`, and `frontend`.

## Inventory semantics

- `actual_quantity` is signed inventory movement quantity. Outgoing movement types keep the signs defined in `OUTGOING_MOVEMENT_TYPES`.
- `reserved_quantity` sums reservations for Sales Orders in `confirmed`, `production`, and `shipped`.
- `available_quantity = actual_quantity - reserved_quantity`. Negative availability is kept as-is.
- `in_transit_quantity` is the remaining quantity on `ordered` and `partial` Purchase Order lines. Reversed GoodsReceipts are excluded; a line's remaining quantity is clamped at zero before aggregation.
- In-transit quantity is displayed separately and never included in available quantity.
- Quote creation and inventory preview do not create InventoryReservation rows. Reservation continues to belong to the formal Sales Order flow.

## Backend API and query behavior

`bulk_sku_metrics(sku_ids)` is in `crm.services.fulfillment` beside the existing fulfillment metrics. It returns all four Decimal metrics using grouped inventory-movement, reservation, and Purchase Order queries. Receipt totals are correlated by Purchase Order line. It does not call `sku_metrics()` once per SKU.

`POST /api/quotes/availability-preview/` accepts `{ "sku_ids": [12, 18] }`, requires 1–200 positive integer IDs, deduplicates IDs, preserves request ordering, and returns HTTP 400 for unknown IDs. It does not require a Quote, customer, price, or line quantity and performs no business writes.

`GET /api/quotes/{id}/availability/` now uses the same bulk helper. Existing `quote_item`, `sku`, `available_quantity`, and `reference_lead_time_days` remain; the latter still comes from `quote.lead_time_days`. The legacy available value retains its Decimal response-data type. The endpoint is enriched with actual, reserved, and in-transit metrics.

## Quote editor

`QuoteEditorModal` requests availability once for the unique selected SKU set when it opens with preselected lines or when the selected SKU set changes. Quantity, unit-price, and description edits do not refetch inventory. Older responses are ignored after a selection change. The panel clears when no SKU remains and includes a manual refresh button and last-refresh time; it does not poll.

Quote demand is aggregated across every line for each SKU with the existing `baseQuantity(item)` utility. Mixed TradeUnit lines therefore compare in the SKU base unit. The inventory panel shows actual, reserved, available, total Quote demand, in-transit, coverage, or shortage. It states that stock is advisory, Quotes do not lock stock, in-transit is excluded from current availability, and final stock/purchase state is checked at order confirmation. The Quote's existing `lead_time_days` appears as the commercial Quote reference lead time.

If the preview request fails, the editor shows `库存参考暂时无法读取，可继续报价。` and keeps Quote save, preview, and export actions available.

## Automated verification

Backend test file: `backend/crm/tests/test_quote_availability.py`.

It covers signed stock, active reservation statuses, negative availability, open Purchase Order statuses, reversed receipts, in-transit separation, multi-SKU and duplicate request IDs, validation and unknown SKU errors, preview read-only behavior, Quote creation without reservation, saved Quote compatibility, shared metric values, and bounded query growth.

Frontend test file: `frontend/tests/quote-editor-availability.spec.js` (12 focused cases). It covers empty and selected SKU sets, unique bulk IDs, removal, stale responses, displayed metrics, coverage and shortage, negative availability, local quantity recalculation, duplicate line aggregation, `baseQuantity` trade-unit conversion, manual refresh, API failure with usable save, related Customer creation, revision preload, and advisory wording.

## Real UI UAT (Browser plugin)

All UAT editors were cancelled without saving a Quote. No inventory or purchase data was changed.

| Case | Result | Evidence / notes |
| --- | --- | --- |
| UAT-P2D-001 — Unsaved Quote | PASS | New Quote with `UAT-R1-CSV-SKU-001` loaded before save: actual 0, reserved 0, available 0, in-transit 0 pcs. |
| UAT-P2D-002 — Compare with Inventory | PASS | Inventory page showed the same SKU at actual 0, reserved 0, available 0, in-transit 0 pcs. |
| UAT-P2D-003 — Demand coverage | PASS, zero-stock boundary | Existing active UAT SKUs both had available 0. Setting demand to 0 displayed coverage at equality; changing demand to 1 displayed shortage 1 immediately. Automated frontend coverage also verifies positive covered demand. |
| UAT-P2D-004 — Quote does not lock stock | PASS | For `SKU-000001`, changing draft demand left available at 0; manual refresh returned 0 again. The editor was cancelled. |
| UAT-P2D-005 — In-transit semantics | PASS | Quote showed actual 0.02, reserved 0.02, available 0, and in-transit 7.98 pcs for `SKU-000001`; Inventory showed the same figures. |
| UAT-P2D-006 — Duplicate / Trade Unit demand | PASS | Two unsaved lines: 3 pcs plus 2 five-piece bags = 13 pcs base demand. The panel aggregated both and showed a 13 pcs shortage. |
| UAT-P2D-007 — Manual refresh | PASS | Refresh updated the last-refresh time and retained both line quantities, units, and aggregated 13 pcs demand. |
| UAT-P2D-008 — Related Customer Quote | PASS | Customer detail → 新建报价 inherited the UAT customer/contact and displayed the same availability panel for a selected SKU; cancelled. |
| UAT-P2D-009 — Revision | PASS | Revision editor for `SJ20261005CA001` preloaded its SKU availability before save; cancelled. |
| UAT-P2D-010 — API failure | PASS, automated | Frontend test forces preview failure, checks the advisory message, and confirms Quote save remains available. No live backend failure was induced. |

Screenshot evidence was saved outside the repository at the Codex visualization artifact `pcr008-uat-inventory-reference.jpg`.

## CI and limitations

- No migration is expected; `makemigrations --check --dry-run` reported no changes.
- PCR-008 commit `97ea6917ee8cfc56928c8bff661ce47dcfd9c14b` was pushed to `master` and is present in the private repository. The post-push Actions run number and job results could not be retrieved: the GitHub Actions page returned a signed-out 404, the local `gh` token is invalid, the connected commit-status query returned no checks, and the available workflow-run query only returns PR-triggered runs. The post-push `backend`, `backend-postgres`, and `frontend` results therefore remain unverified; CI #136 above is the user-provided baseline, not the PCR-008 run.
- The local complete Django suite and frontend CI suites are recorded in the delivery response. PostgreSQL CI is run by GitHub Actions; this workstation did not expose a local Docker command/service for reproducing its PostgreSQL service.
- UAT inventory data had no positive available quantity, so the real UI coverage check used the exact zero-demand/zero-available boundary, then verified a positive shortage. Positive covered demand is covered by the frontend automated test.
- PCR-008 does not introduce procurement lead-time estimates, stock history, allocation, reservation, or polling.
