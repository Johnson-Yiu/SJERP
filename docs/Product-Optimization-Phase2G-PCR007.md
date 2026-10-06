# SUNJACK-ERP — Phase 2G / PCR-007 — Actual Shipment Packing

Baseline: `master` at `737a6ab16a64c7ddf7cb3257f1dc10d1ad3edd38`.
Baseline CI #148: backend, backend-postgres, frontend **SUCCESS**.

## Scope and data semantics

The Order workspace previously exposed only an estimated Order-level
`PackingPlan`. Existing `ShipmentPackage`, `ShipmentPackageItem`, package
GET/create/update APIs, and estimated-plan copying were not connected to a
formal actual-packing UI. The existing copy also deleted actual packages and
copied a whole Order plan into any Shipment without comparing quantities.

The workspace tab is now **装箱**, retaining the existing **预计装箱** UI and
adding a separate **实际装箱** section organized by Shipment. Packaging
Templates remain reusable rules; PackingPlan remains an Order estimate;
ShipmentPackage records how one specific Shipment was actually packed.
Actual packing never changes estimated packing, Order/Shipment quantities,
inventory, reservations, financial plans, or settlements. No new table or
migration was required.

## Actual packing workflow

- Opening the Packing tab lazily loads `GET /shipments/<id>/packages/` for
  each Shipment. The Order workspace caches the returned packages across tab
  switches; successful edits/delete reload only their Shipment. Reopening or
  refreshing the workspace fetches current data. Failed loads offer retry.
- Each card shows Shipment number, date, status, aggregated shipped SKUs,
  carton count, net/gross weight, CBM, and packed/shipped/unpacked quantities.
- One shared editor handles add/edit: carton number, dimensions, actual
  weights, notes, and multiple distinct shipped SKUs with base quantities.
  A new carton defaults to `max(existing carton_no) + 1`.
- The selector uses the target Shipment's SKUs, aggregating repeated
  ShipmentItem lines. Display prefers InventoryMovement shipment snapshots,
  then existing OrderItem snapshots. No duplicate SKU identity columns were
  added to ShipmentPackageItem.
- Delete uses one App confirmation and the scoped package DELETE endpoint.
  Canceling makes no request. Only the packing record is removed.
- Summary arithmetic uses scaled BigInt decimals; entry keeps decimal text.
  No duplicate persisted summary was introduced, and CBM is server-calculated.

## Server protection and transactions

All create/update/delete/copy mutations require a confirmed Shipment. GET
history remains available after reversal. Mutations lock the Shipment row,
using the same lock as Shipment reversal, and run inside database transactions.

Validation rejects nonpositive or duplicate carton numbers, nonpositive
quantities, SKUs absent from the Shipment, duplicate SKUs in one carton, and
cumulative packed quantity exceeding the SKU's aggregated shipped quantity.
Editing excludes that carton's existing items before checking replacement
values. Partial packing is valid and its remaining quantity is displayed.
Dimensions must all be blank or all positive. Weights must be nonnegative,
and gross weight cannot be below net weight. Duplicate carton numbers produce
a clear business error rather than a raw database constraint error.

The existing update endpoint still accepts POST; scoped PUT/PATCH and DELETE
are also supported. Both field changes and item replacement are atomic.
Automated failure injection verifies rollback of create, update, delete and
copy, including a copy failure after the first replacement carton was saved.

Copy compares PackingPlan carton-item totals by SKU with confirmed
ShipmentItem totals by SKU; the maps must be exactly equal. Partial shipments
and incomplete/mismatched plans are blocked with the explicit manual-entry
explanation. Existing packages require the literal boolean `replace: true`;
the frontend asks for one replacement confirmation. Copy reuses the actual
package validation rules and copies dimensions, quantities and estimated
weights as independent editable actual values. Regenerating the estimate does
not rewrite actual packages. There is no proportional splitting.

Reversal retains actual packages as history. Cancelled Shipment cards show
**发货已冲销 · 实际箱单仅供历史查看** and no add/edit/delete/copy controls.
Server tests verify the write guard as well as preservation during reversal.

## Real UI UAT — 2026-10-07

Performed with the built-in Browser skill against disposable existing UAT
records through normal UI. No Shipment was created, reversed or deleted for
this task. No inventory or payment entry was performed.

| UAT | Result | Evidence |
|---|---|---|
| UAT-P2G-001 | PASS | `SO-2026-00034` → 装箱 clearly separated 预计装箱 / 实际装箱; the expected-plan UI remains. |
| UAT-P2G-002 | PASS | Confirmed `SH-9F7865E1ED814C24`, 2026-10-05, `UAT-R1-CSV-SKU-001`, shipped 1 pcs, displayed under the correct Order. |
| UAT-P2G-003 | PASS | Created disposable carton 1: 20 × 10 × 5 cm, net 0.2 kg, gross 0.3 kg, SKU quantity 0.5. Backend CBM 0.001000 m³ appeared. |
| UAT-P2G-004 | PASS | Edited length to 25 cm, net/gross to 0.25/0.4 kg, quantity to 0.75; closed and reopened the Order and confirmed persistence, including CBM 0.001250 m³. |
| UAT-P2G-005 | PASS | Displayed packed 0.75 / shipped 1 pcs / remaining 0.25 pcs. |
| UAT-P2G-006 | PASS — automated branch | Available selected confirmed UAT shipments were single-SKU; mixed-SKU creation and payload handling passed backend/frontend tests. The existing multi-SKU batch Shipment inspected in UAT-009 was reversed and not used for writes. |
| UAT-P2G-007 | PASS | Tried updating to 2 pcs against shipped 1. Server rejected with the cumulative-quantity business error; editor remained usable, previous 0.75 and physical values remained. |
| UAT-P2G-008 | PASS — partial Shipment branch | `SO-2026-00026` had three confirmed shipments. Its generated Order estimate showed 10 cartons. Copy to `SH-C15BCCBCAED94A98` (60 pcs) was rejected with the explicit whole-Order/mismatched-Shipment/manual-entry explanation. Exact-copy success is automated. Incomplete plan copying on SO-00034 was also rejected, including after its one replacement confirmation. |
| UAT-P2G-009 | PASS | Cancelled disposable `SO-2026-00036` / reversed `SH-E59265871A1D47E0` showed its two historical SKUs and read-only notice with no mutation controls. It had no packages; automated reversal test verifies package preservation. |
| UAT-P2G-010 | PASS | Deleted the temporary actual carton using App confirmation. Count/net/gross/CBM returned to zero, shipped quantity stayed 1, and before/after inventory table remained identical: `SH-4095D817AD4943DD`, sale_out, -1.00. No copied actual cartons were created. |

UAT generated disposable expected-plan snapshots for SO-00034 (missing
packaging configuration, no cartons) and SO-00026 (10 cartons) using the normal
existing generation UI. Packaging Templates and SKU packaging profiles were
not modified. All actual packing records created by this UAT were cleaned up.

## Automated and regression evidence

- New backend tests cover the required item/carton/quantity/physical rules,
  editable copying, replacement intent, reversal history, historical display,
  plan independence and transaction rollback. Two existing packing fixtures
  now contain confirmed ShipmentItems, as required by the new safety rules.
- Frontend actual-packing suite: **22 passed**, including lazy/scoped cached
  loading, management guards, mixed payloads, editor recovery, confirmation
  cancellation, exact decimal summaries and retained expected-packing UI.
- Local full backend: **550 tests, OK (10 skipped)**, including **26 new
  actual-packing tests**. PostgreSQL-specific skipped checks are verified by CI.
- Local full Node suite: **111 passed**; Node typography test: **1 passed**.
- Local full Vitest: **162 passed across 22 files**.
- Frontend build: **passed** (existing large-chunk advisory).
- Django system check and `makemigrations --check --dry-run`: **passed**;
  **No changes detected**.
- Full suites include PCR-006 batch Shipment, reversal, fulfillment/inventory,
  Trade Unit shipment, PackingPlan/Template management, and PCR-020 navigation.

## CI and status

Live UAT: **PASS**. Final GitHub Actions verification is pending the normal
commit/push. PCR-007 is not closed until the final required backend,
backend-postgres and frontend jobs all succeed.

Remaining limitation: formal Packing List PDF/Excel export is not implemented.
No invoices, labels, barcodes, carriers, picking or container-loading features
were introduced. PCR-019 has not been started.
