# SUNJACK-ERP — Product Optimization Phase 2C-3 PCR-010

## Scope and URL semantics

PCR-010 preserves the selected Inventory SKU when navigating to Sales Orders, Purchase Orders, and Inventory Movements. The query parameter is the numeric SKU ID (`sku=<id>`); the SKU code is presentation text only. Record links add the destination record's numeric ID as `detail=<id>`. No route, model, or migration was added.

Purchase Orders now filter through `items__sku_id` and use `distinct()` so a multi-line Purchase Order appears once. The SKU condition composes with existing `search`, `status`, and `pending_receipt` filters. The Purchase Order page sends `sku` to the list endpoint and excludes `detail` from API parameters. Orders and Inventory Movements continue to use their existing route-data query handling.

## Inventory navigation and destination context

The selected SKU drawer includes contextual links to its filtered Purchase Orders, Sales Orders, and Inventory Movements. Movement numbers, Purchase Order numbers, related Order numbers, and shipment Order numbers link to the existing destination list with both SKU and record IDs. Shipment rows expose only the lightweight Sales Order ID needed for the link. Table rows remain non-clickable.

Orders, Purchase Orders, and the Inventory Movements ResourcePage show a current-SKU indicator. Its label is derived from loaded filtered records when available, with `SKU #<id>` as a fallback. Clearing the context removes only `sku` and preserves other route query state. Closing a detail view removes `detail` while retaining `sku`.

## Real UI UAT

Tested against existing SKU `SKU-000001` (ID `1`). Its Inventory detail showed 15 Purchase Orders, 31 related Sales Orders, 63 Inventory Movements, and 29 shipment records. No business data was changed during this navigation UAT.

| Case | Result and evidence |
| --- | --- |
| UAT-P2C3-001 | **PASS** — Inventory drawer → Purchase Orders opened `/purchase-orders?sku=1`; indicator showed `SKU-000001`; 15 matching Purchase Orders were listed. |
| UAT-P2C3-002 | **PASS** — Inventory drawer → Sales Orders opened `/orders?sku=1`; indicator showed `SKU-000001`; the filtered list contained 31 Orders. |
| UAT-P2C3-003 | **PASS** — Inventory drawer → Movements opened `/inventory-movements?sku=1`; 63 visible movement rows all displayed `SKU-000001`. |
| UAT-P2C3-004 | **PASS** — Purchase `PO-2026-00019` opened `/purchase-orders?sku=1&detail=19`; closing it returned to `/purchase-orders?sku=1`. |
| UAT-P2C3-005 | **PASS** — Order `SO-2026-00033` opened `/orders?sku=1&detail=33`; closing the workbench retained `/orders?sku=1`. |
| UAT-P2C3-006 | **PASS** — Movement `GR-BC0D4E04B9CE4171` opened `/inventory-movements?sku=1&detail=75`; closing its detail retained `/inventory-movements?sku=1`. |
| UAT-P2C3-007 | **PASS** — Shipment Order `SO-2026-00030` opened the Sales Order workbench at `/orders?sku=1&detail=30`. |
| UAT-P2C3-008 | **PASS** — SKU was cleared on all three destination pages. On Orders, `status=production` remained; on Purchase Orders, `detail=19` remained. On Movements, the detail overlay was closed before using the clear action, which returned to `/inventory-movements`. |
| UAT-P2C3-009 | **PASS** — Directly opened and refreshed `/purchase-orders?sku=1`, `/orders?sku=1`, and `/inventory-movements?sku=1`; each retained its SKU indicator and filtered rows (15, 31, and 63 respectively). |
| UAT-P2C3-010 | **PASS** — From the SKU drawer, navigated to `/orders?sku=1`, used browser Back to return to `/inventory`, then Forward restored `/orders?sku=1`, the `SKU-000001` indicator, and 31 filtered Orders. |

## Automated verification

- Focused backend tests: `crm.tests.test_inventory_sku_context_navigation` — 4 passed, covering inclusion/exclusion, duplicate suppression for multi-line POs, SKU combined with status/pending receipt/search, and inventory-detail navigation IDs including shipment Order ID.
- Full backend suite: 508 passed, 10 skipped. `manage.py check` reported no issues; `makemigrations --check --dry-run` reported no model changes.
- Focused frontend route tests: `tests/pcr010-inventory-navigation.spec.js`, `tests/purchase-order-filters.spec.js`, and `tests/route-lifecycle.spec.js` — 30 passed.
- Frontend unit suite passed; the separate `tests/detail-drawer-typography.spec.js` check passed; all Vitest tests under `tests` passed (96 tests across 16 files, excluding the separately run typography test).
- `npm run build` succeeded.

## CI and limitations

Baseline CI #129 passed all three jobs (`backend`, `backend-postgres`, `frontend`). The PCR-010 commit's CI result will be recorded here after push and completion of its workflow run.

The local production build reports Vite's existing bundle-size advisory for a chunk above 500 KB. No database migration is required. The UI UAT used existing local development data and verified navigation/filter context; it did not create or modify business records.
