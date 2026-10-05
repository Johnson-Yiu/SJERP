# SUNJACK-ERP — Product Optimization Phase 2B-1 / PCR-003

Updated: 2026-10-05
Scope: Purchase Order list search, status, and pending-receipt filters only.

## Implementation

- The existing DRF `SearchFilter` and `search_fields` remain the search implementation for purchase number, supplier name, and source sales order number.
- `PurchaseOrderViewSet.get_queryset()` supports exact `status` filtering and `pending_receipt=1`. Pending receipt means the existing lifecycle statuses `ordered` or `partial`; no field or migration was added.
- The purchase list has a 300 ms debounced search, a status selector, a pending-receipt checkbox, and a reset action. The controls combine as normal query parameters.
- Initial page load fetches purchase rows plus supplier, order, and SKU reference options. Search and filter changes fetch purchase rows only. Reference data is refreshed only on initial load or explicit page refresh.
- New list requests supersede older responses. If a filtered result removes the expanded purchase, its detail row closes. Summary cards label their values as the current filtered result.

## Real UI UAT

Cases were run in the Browser plugin against the local app at `http://127.0.0.1:5192/purchase-orders`. Only list GETs were issued for filtering. Modals and confirmation prompts were opened and cancelled; no purchase, receipt, payment, cancellation, or deletion was submitted.

| Case | Observed result | Status |
|---|---|---|
| UAT-P2B1-001 — purchase number | Search `PO-2026-00001` showed only that row; clearing search restored all 18 purchases. | PASS |
| UAT-P2B1-002 — supplier | Search `UAT 供应商 B-历史快照测试` returned 7 rows; every row had the matching supplier. | PASS |
| UAT-P2B1-003 — source order | Search `SO-2026-00026` returned `PO-2026-00015` and `PO-2026-00014`. | PASS |
| UAT-P2B1-004 — status | 草稿 returned `PO-2026-00004` (1); 已下单 returned `PO-2026-00005` (1); 已完成 returned 15. Every visible row matched its selected status. | PASS |
| UAT-P2B1-005 — pending receipt | Only `PO-2026-00006` (部分到货) and `PO-2026-00005` (已下单) appeared; draft and completed rows were excluded. | PASS |
| UAT-P2B1-006 — combined filters | Search `PO-2026-00006` with 仅看待到货 enabled returned only that partial-receipt purchase. | PASS |
| UAT-P2B1-007 — working context | Expanded and collapsed the filtered purchase row, then opened and cancelled 新建采购单. Search, pending checkbox, and matching row remained unchanged. | PASS |

### Procurement action regression

- 新建采购单 opened and cancelled.
- 编辑草稿 opened for `PO-2026-00004` and cancelled.
- 确认下单 opened its confirmation prompt and cancelled before submission.
- 验货入库 opened for `PO-2026-00006` and cancelled.
- 登记付款 opened for `PO-2026-00006` and cancelled.

## Automated verification

| Check | Result |
|---|---|
| Focused Django filter tests | PASS — 6 tests |
| Full Django SQLite suite | PASS — 478 tests, 10 skipped by project configuration |
| Focused purchase filter component tests | PASS — 4 tests |
| Frontend Node unit suite | PASS — 109 tests |
| Frontend Vitest suite | PASS — 71 tests across 12 files (excluding the standalone Node typography spec) |
| Frontend production build | PASS — existing large-chunk advisory remains |
| Django system check | PASS — no issues |
| Migration check | PASS — no changes detected |

## Limitations

- Search remains the existing DRF `SearchFilter`; its match behavior and case handling are unchanged.
- Summary cards intentionally describe only the currently filtered rows, not global totals.
- No pagination, lifecycle redesign, new model field, or migration was introduced.
