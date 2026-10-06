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

## Historical read-only UI inspection — 2026-10-06

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

At that earlier read-only inspection, the Inventory page showed two SKUs, **0 available stock**, and actual stock of only `0.02 pcs` fully reserved for `SKU-000001`; the second SKU had no stock. The active UAT order inspected had one line, with `0.01` allocated and `10` remaining. The remaining active orders were also single-line. The only in-transit stock belongs to an existing purchase and was not treated as available stock. No existing customer Order was modified, and no stock adjustment was made during that earlier inspection. The disposable live UAT attempt below supersedes the earlier “not run” status where it records additional evidence.

## Disposable live UAT attempt — 2026-10-06

The attempt used the normal ERP UI and created one disposable two-line order. It did not use an API, database, Django shell, or fixture shortcut. The existing active orders were left untouched.

### UAT Cleanup Baseline

Inventory values recorded from the Inventory page before creating temporary stock:

| SKU | Product | Actual | Reserved | Available |
|---|---|---:|---:|---:|
| `SKU-000001` | UAT-R1 智能面板灯-12W-3000K | 0.02 pcs | 0.02 pcs | 0 pcs |
| `UAT-R1-CSV-SKU-001` | UAT-R1 CSV Product No Category-Demo specification | 0 pcs | 0 pcs | 0 pcs |

UAT customer: `UAT-R1 客户 Alpha GmbH`.

### Temporary stock and dedicated order

Temporary manual stock-in adjustments were created through Inventory with the reference `PCR-006 TEMP UAT STOCK`:

| Movement | SKU | Quantity | Cleanup result |
|---|---|---:|---|
| `IM-3697213DBA9246C0` | `SKU-000001` | +11 pcs | Remains active; reversal was not attempted after the UI safely blocked reversal of the later A adjustment. |
| `IM-B3FFBA2513D44997` | `SKU-000001` | +10 pcs | Remains active; reversal was rejected because available stock was insufficient while existing reservations remained. |
| `IM-3A8C96F21E044EF8` | `UAT-R1-CSV-SKU-001` | +9 pcs | Reversed in the UI as `REV-3C698280C8274465`; SKU B returned to baseline. |

The dedicated order was `SO-2026-00035`, created and confirmed through Orders for `UAT-R1 客户 Alpha GmbH`. The UI showed OrderItem `#38` for SKU A, 10 pcs, and OrderItem `#39` for SKU B, 8 pcs. After confirmation, the procurement and shipment view showed:

- SKU A: ordered 10, reserved 0, to procure 10; this line did not have free stock for live shipment.
- SKU B: ordered 8, reserved 8, to procure 0.

The first +11 pcs of SKU A were consumed by reservations on older active orders. A further +10 pcs also left SKU A with 0 available, 21.02 actual, and 21.02 reserved. No existing order or purchase order was changed. Because the dedicated Order could not obtain the 10 pcs reservation required for a safe full shipment, no Shipment was submitted.

### Live UAT results

| UAT | Result | Evidence / limitation |
|---|---|---|
| UAT-P2E-001 — Open batch shipment | **PARTIAL** | The shared dialog opened and displayed both OrderItems, initially selected, with remaining quantities 10 pcs and 8 pcs. SKU A had 0 reserved and 10 to procure, so the two lines were not both ready to ship; independent quantity editing was not fully exercised. |
| UAT-P2E-002 — Selection | **PARTIAL** | Unchecking SKU B changed selected count from 2 to 1 and left SKU A selected. The line was not re-selected before the dialog was canceled. |
| UAT-P2E-003 — Partial + full in one batch | **NOT RUN** | No batch was submitted because SKU A had 0 reserved and 10 to procure. No stock-shortage submission was attempted. |
| UAT-P2E-004 — One shipment history card | **NOT RUN** | No Shipment was created. |
| UAT-P2E-005 — Fulfillment quantities | **NOT RUN** | No Shipment was created. |
| UAT-P2E-006 — Inventory movements | **NOT RUN** | No Shipment or sale-out movements were created. |
| UAT-P2E-007 — Row-level regression | **PARTIAL** | From the row-level SKU B action, the shared dialog opened with only OrderItem `#39` checked and SKU A `#38` unchecked; it was canceled. The post-partial remaining-quantity state could not be tested because no Shipment was created. |
| UAT-P2E-008 — Trade Unit | **PASS — live UI** | SKU A's existing `10 pcs / 箱` Trade Unit displayed `1 箱 = 10 pcs`; quantity 1 showed “交易数量 1 箱，折合 10 pcs” in the shared dialog. Nothing was submitted. |
| UAT-P2E-009 — Error atomicity | **PASS — automated evidence** | The existing automated test `test_multi_line_batch_stock_failure_rolls_back_earlier_line_and_reservation` remains the evidence. No live inventory was deliberately damaged. |
| UAT-P2E-010 — Multi-line reversal | **NOT RUN** | No live Shipment existed to reverse. Automated API reversal coverage remains passing. |

### Cleanup and final inventory

The dedicated Order was canceled through the UI with reason `PCR-006 UAT CLEANUP`. The Order displays `已取消`; its SKU B reservation was released. There was no Shipment to reverse and no shipment history record was created.

The SKU B stock adjustment was safely reversed through Inventory with reason `PCR-006 TEMP UAT STOCK CLEANUP`, producing reversal movement `REV-3C698280C8274465`. When the same UI was used to reverse SKU A movement `IM-B3FFBA2513D44997`, it rejected the operation with: “当前可用库存不足，无法完整冲销该流水；请先处理相关预留/业务单据。” Per the task's safety instruction, no existing reservation/order was changed and no API/database workaround was attempted. The other SKU A movement `IM-3697213DBA9246C0` remains active and its reversal was not attempted after this safety block.

Final values shown by the Inventory page:

| SKU | Baseline actual / reserved / available | Final actual / reserved / available | Delta |
|---|---|---|---|
| `SKU-000001` | 0.02 / 0.02 / 0 pcs | 21.02 / 21.02 / 0 pcs | +21 actual, +21 reserved, 0 available |
| `UAT-R1-CSV-SKU-001` | 0 / 0 / 0 pcs | 0 / 0 / 0 pcs | 0; returned to baseline |

The stock delta for SKU A is unresolved UAT data, not a claim of completed cleanup. PCR-006 remains **OPEN / NOT PASS**. The next safe completion requires a disposable SKU/order setup whose stock can be reserved for the UAT order without displacing earlier active reservations, and whose temporary inventory can then be safely reversed through the UI.

PCR-006 is **not marked PASS** until UAT-P2E-001 through UAT-P2E-006 and UAT-P2E-010 can be completed with one disposable multi-line UAT Order and adequate free stock, followed by reversal of that same Shipment. The present test data does not satisfy those preconditions.

## Previous UAT contamination recovery — 2026-10-06

This recovery phase followed the isolated-UAT instructions. All inspection and the attempted cancellation used the normal ERP UI. No API, database, Django shell, fixture, order-quantity edit, or inventory adjustment was used.

### Orders consuming `SKU-000001` reservations

The Inventory → `SKU-000001` → 关联订单 view showed three older active orders after the disposable `SO-2026-00035` was canceled. Their line quantities, reserved amounts, shipped amounts, and activity were checked in each Order workspace.

| Order | Customer / status | Ordered / reserved / shipped | Payment and receivable | Shipment | Procurement / receipt | UAT classification and recovery decision |
|---|---|---:|---|---|---|---|
| `SO-2026-00031` | `UAT-R1 客户 Alpha GmbH` / 生产中 | 10 / 10 / 0 pcs | Paid USD 0; open receivable plan USD 10 | None; inventory movement count 0 | No linked Purchase Order or receipt | Clearly UAT order; not canceled after SO-33 triggered the safety stop. |
| `SO-2026-00032` | `UAT-R1 客户 Alpha GmbH` / 已确认 | 10 / 10 / 0 pcs | Paid USD 0; open receivable plan USD 10 | None; inventory movement count 0 | No linked Purchase Order or receipt | Clearly UAT order; not canceled after SO-33 triggered the safety stop. |
| `SO-2026-00033` | `UAT-R1 客户 Alpha GmbH` / 已确认 | 10 / 1.02 / 0 pcs | Paid USD 0; open receivable plan USD 10 | None; inventory movement count 1 (procurement receipt context, no sale-out) | Linked `PO-2026-00019`, supplier `UAT 供应商 A`, USD 0.10; 1.00 pcs ordered, 0.01 pcs received on 2026-10-05, 0.99 pcs outstanding, USD 0.10 unpaid | Customer, supplier, amount, and context identify UAT data. However, ERP rejected cancellation because a formal procurement record is linked; preserved without modification. |

The current reserved quantities total `21.02 pcs` (10 + 10 + 1.02), matching Inventory's aggregate reserved amount. The screen evidence is consistent with temporary stock being allocated through the normal reservation process to older active demand. This is expected reservation behavior, not an observed PCR-006 production defect.

### Recovery safety gate and inventory result

Cancellation of `SO-2026-00033` was attempted through its Order workspace with reason `PCR-006 PREVIOUS UAT CLEANUP`. ERP refused with: `订单已有正式采购记录，不能直接取消。` The order remained **已确认**, with its linked PO and receipt intact. `SO-2026-00031` and `SO-2026-00032` were not canceled because not all reservation consumers passed the safety gate. The two active `SKU-000001` stock-in movements (`IM-3697213DBA9246C0` +11 and `IM-B3FFBA2513D44997` +10) were not reversed during this recovery phase. No PO, receipt, shipment, payment, order quantity, or reservation was edited.

The Inventory page still showed `SKU-000001` actual `21.02 pcs`, reserved `21.02 pcs`, available `0 pcs`, against the pre-UAT baseline `0.02 / 0.02 / 0 pcs`. Baseline is **not restored**; the unresolved delta remains `+21 pcs` actual and reserved. `UAT-R1-CSV-SKU-001` remains at `0 / 0 / 0 pcs`; its earlier +9 temporary movement is reversed as recorded above.

Per the safety gate, recovery stopped here. No isolated SKU was created, no new UAT stock or order was added, and no new Shipment UAT was attempted. This branch is blocked by the linked formal procurement record on `SO-2026-00033`; PCR-006 remains **OPEN / NOT PASS** until the contaminated stock can be safely recovered and the isolated live UAT can be completed.

## CI and limitations

GitHub Actions **run #142** for implementation commit `255245118237df9062a7dbf3bc59f90654ba51b9` completed successfully before this documentation-only UAT update:

- `backend`: success
- `backend-postgres`: success
- `frontend`: success

PCR-006 remains open while the mandatory multi-line live UAT is unavailable, even if automated suites and CI pass.
