# SUNJACK-ERP — Product Optimization Phase 2F / PCR-020

Baseline: `master` at `c8d2866516164be5371e93701ac2b8dcd0e899b1`; baseline CI #146 passed for backend, backend-postgres, and frontend.

## Problem and workflow

Before PCR-020, the Order workspace showed receivable plans, collected amount,
and outstanding balance, but users had to open Finance and search the Order
again. The Order workspace now shows **查看 / 登记本单应收** in its existing
回款进度 card when an eligible Order has an outstanding balance. The link
navigates to `/receivables?order=<ORDER_ID>` and leaves receivable settlement
to the existing Receivables page and PaymentPlan settle endpoint.

The action is hidden when the balance is zero or negative, or the Order is a
draft or cancelled. Shipped and completed Orders with an outstanding balance
remain eligible. No payment dialog, settlement logic, schema, or backend code
was added or changed.

## Route context and backend reuse

`PaymentPlanPage.vue` reads `order` from the Vue Router query on Receivables
only. Each list request uses the existing server-side endpoint and includes
`direction=receivable&order=<id>` along with the active status, overdue, search,
and due-date filters. The existing `PaymentPlanViewSet` order filter is reused;
the page does not download all plans and filter them locally. Payables ignores
sales-order query context and retains its existing purchase-order links and
filters.

For a syntactically valid numeric ID, the page fetches the Order through the
existing detail endpoint and displays its server-returned Order number in a
banner. This avoids presenting arbitrary query text as an Order number and
still shows an understandable load error if the Order cannot be fetched. A
malformed ID fails closed with an error and clear action rather than showing an
unscoped list. **查看订单** uses the existing `/orders?detail=<id>` navigation
helper. **清除订单筛选** removes only `order` from the route query, retains
other query values, and reloads Receivables without a browser reload.

## Automated verification

Added focused coverage for CTA eligibility and target, direct route context,
trusted banner Order number, return navigation, clearing context, filter
continuity, malformed and missing Orders, Payables isolation, and the existing
settlement dialog.

Local frontend checks:

- `npm run test:unit`: **111 passed**.
- `node --test tests/detail-drawer-typography.spec.js`: **1 passed**.
- Full Vitest suite: **140 passed across 21 files**.
- `npm run build`: **passed**. Vite emitted the existing large-chunk advisory.

Backend source and settlement accounting were unchanged. GitHub Actions for
the implementation and UAT evidence commit is pending; its run number and
three job conclusions will be recorded after the push.

## Real UI UAT — 2026-10-06

UAT used existing disposable UAT orders through the in-app Browser. No payment
was submitted and no business data was changed.

The outstanding example was `SO-2026-00034`, a shipped UAT order with USD 9.90
outstanding. Its scoped Receivables list showed exactly two plans for that
Order: USD 6.93 due 2026-10-04 and USD 2.97 due 2026-10-05.

| UAT | Result | Evidence |
|---|---|---|
| P2F-001 — CTA on outstanding Order | **PASS** | Shipped `SO-2026-00034` showed **查看 / 登记本单应收** below its 回款进度 values. |
| P2F-002 — Direct scoping | **PASS** | Clicking opened `/receivables?order=34` without manual search. |
| P2F-003 — Context banner | **PASS** | Banner showed `当前仅显示订单：SO-2026-00034`. |
| P2F-004 — Plan ownership | **PASS** | Both displayed plans showed contract `SO-2026-00034`; no other Order appeared. |
| P2F-005 — Filter continuity | **PASS** | Changing status, overdue, date range, and search kept `order=34` and the banner active. |
| P2F-006 — View Order | **PASS** | Banner link returned to `/orders?detail=34` and the same Order workspace. |
| P2F-007 — Clear context | **PASS** | Clear removed `order`, removed the banner, and reloaded the ordinary Receivables list. |
| P2F-008 — Zero balance | **PASS** | Completed `SO-2026-00030` showed USD 0.00 outstanding and no receivable CTA. |
| P2F-009 — Payables | **PASS** | `/payables` showed the normal 21 open purchase payable plans, without a sales-order banner or context. |
| P2F-010 — Settlement form | **PASS** | The first scoped plan opened **登记收款** for `SO-2026-00034` / UAT-R1 客户 Alpha GmbH; the form was canceled without submission. |

Draft/cancelled exclusion and completed-with-balance visibility are covered by
automated component tests; completed zero-balance behavior was also checked in
the live UI. PCR-020 UAT is **PASS**; final closure awaits the required CI run.
