# SUNJACK-ERP Product Optimization — Phase 2E PCR-006

## Scope and implementation

PCR-006 closes the frontend gap in multi-line shipment entry. The existing `confirm_shipment()` service and `POST /orders/{id}/ship/` API already provide one atomic shipment with multiple shipment items, per-line inventory movements, overage handling, reservation consumption, order status updates, and whole-shipment reversal. This work reuses that API; it adds no endpoint, migration, ShipmentPackage UI, or production backend behavior.

`OrderDetailModal` now has one shared shipment dialog and submit path:

- **批量发货** is shown only for confirmed, production, or shipped orders with at least one unshipped line. It opens with all shippable lines selected.
- Each row-level **确认发货** action opens the same dialog with only that OrderItem selected.
- Forms are keyed by OrderItem ID, so repeated SKUs remain separate shipment lines. SKU detail requests are cached per component and deduplicated by SKU ID.
- The user can edit one shipment date for the whole Shipment and adjust each selected line's quantity independently. Quantities start at the line's current unshipped base quantity.
- `TradeUnitPicker`, `baseQuantity()`, and `tradePayload()` retain the existing transaction-unit conversion behavior.
- Over-shipment requires a reason on each affected line. One `confirmDialog` summarizes all overage lines and is the only confirmation used for a batch.
- One submit sends one `POST /orders/{id}/ship/` with only selected OrderItem IDs. Backend failure keeps all selections and entered values in the dialog and shows the returned error; success closes the dialog and reloads workbench and fulfillment data.
- Shipment history continues to show one card per Shipment with all its ShipmentItems. Reversal remains whole-Shipment and uses the existing backend reversal service.

## Automated verification

Focused backend API coverage verifies:

- A one-request multi-SKU shipment creates one Shipment and multiple ShipmentItems and sale-out movements with one Shipment reference; full and partial line quantities remain correct.
- A later line's insufficient stock rolls back earlier line writes and preserves reservations.
- Duplicate OrderItem IDs and OrderItems from another Order are rejected.
- A normal line and customer-addon overage can share a Shipment; only the overage portion creates its supplement and receivable plan.
- The API can reverse a multi-SKU Shipment as a whole and restore order status, all inventory, and reservations.

Existing trade-unit tests cover same-SKU order lines with different package units in one shipment. New frontend Vitest coverage verifies order-state gating, initial selection, row-level dialog reuse, partial quantities, repeated-SKU identity, request count/payload, SKU lookup deduplication, TradeUnit conversion, per-line overage reasons, one app confirmation, retained values after failure, successful reload, and one history card containing multiple items.

Local checks completed so far:

- Focused backend `FulfillmentApiTests`: **24 passed**.
- Focused batch-shipment Vitest: **10 passed**.
- Frontend Vitest suite: **125 passed**.
- Frontend Node tests: **111 passed**.
- Detail drawer typography check: **1 passed**.
- Frontend production build: **passed** (Vite reports a large JavaScript chunk advisory).
- `makemigrations --check --dry-run`: **no changes detected**.
- Full Django discovery suite `python manage.py test --noinput`: **524 passed, 10 skipped**; system checks clean.

## Real UI UAT — 2026-10-06

The in-app Browser was used for UI inspection. No order, shipment, or inventory data was changed during this inspection.

| UAT | Result | Evidence / limitation |
|---|---|---|
| UAT-P2E-001 — Open batch shipment | **NOT PASSED** | The batch action and shared dialog opened on UAT order `SO-2026-00033`, but that order has only one line. It is not a valid multi-line batch UAT order. |
| UAT-P2E-002 — Selection | **NOT RUN** | No suitable multi-line UAT order was available. Automated selection and payload coverage passed. |
| UAT-P2E-003 — Partial + full in one batch | **NOT RUN** | No suitable multi-line UAT order with sufficient free stock was available. |
| UAT-P2E-004 — One shipment history card | **NOT RUN** | Depends on the successful batch in UAT-P2E-003. |
| UAT-P2E-005 — Fulfillment quantities | **NOT RUN** | Depends on the successful batch in UAT-P2E-003. |
| UAT-P2E-006 — Inventory movements | **NOT RUN** | Depends on the successful batch in UAT-P2E-003. |
| UAT-P2E-007 — Row-level regression | **PASS — read-only UI check** | On `SO-2026-00033`, row-level **确认发货** opened the shared dialog with only OrderItem `#36` checked. The dialog was canceled without saving. |
| UAT-P2E-008 — Trade Unit | **PASS — automated evidence** | The local order was not a suitable shipment candidate; automated frontend TradeUnit conversion and existing same-SKU, multi-package backend shipment coverage passed. |
| UAT-P2E-009 — Error atomicity | **PASS — automated evidence** | The multi-line API stock-failure test verified the whole batch rolls back and leaves reservations unchanged. |
| UAT-P2E-010 — Multi-line reversal | **NOT PASSED in live UAT** | The API regression test passed, but no dedicated live multi-line Shipment was created, so there was no safe UAT Shipment to reverse. |

At inspection, the Inventory page showed two SKUs, **0 available stock**, and actual stock of only `0.02 pcs` fully reserved for `SKU-000001`; the second SKU had no stock. The active UAT order inspected had one line, with `0.01` allocated and `10` remaining. The remaining active orders were also single-line. The only in-transit stock belongs to an existing purchase and was not treated as available stock. No existing customer Order was modified, and no stock adjustment was made to manufacture UAT inventory.

PCR-006 is **not marked PASS** until UAT-P2E-001 through UAT-P2E-006 and UAT-P2E-010 can be completed with one disposable multi-line UAT Order and adequate free stock, followed by reversal of that same Shipment. The present test data does not satisfy those preconditions.

## CI and limitations

GitHub Actions **run #141** for implementation commit `2d68a452f6200908f8f56e9adae7bf1a85002f1a` completed successfully:

- `backend`: success
- `backend-postgres`: success
- `frontend`: success

PCR-006 remains open while the mandatory multi-line live UAT is unavailable, even if automated suites and CI pass.
