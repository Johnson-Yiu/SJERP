# R0-D4B2-A Focused Repair Evidence

- Base: 2a9d6cded67ffb4691f3741ea35ee712ce1f9d42
- Final master commit: 073d3a612b7ff333abe7dcd48487f7b35dd5706e
- Final CI: https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38208167344
- Backend: SUCCESS, 680 tests (10 existing SQLite skips).
- Backend PostgreSQL: SUCCESS, 680 tests.
- Frontend: SUCCESS, 121 Node tests + 1 typography check, 49 Vitest files / 491 tests, and production build.
- Additional Backend API JSON regressions: 11 passed.
- Browser: Codex built-in Chromium, actual server-authenticated sessions.
- Test data: standalone focused-ui.sqlite3 in the isolated worktree, synthetic customers, supplier, purchases, plans, and a 20 CNY payment fixture. No production data or developer access settings changed.

## Screenshot matrix

| Screenshot | Verification |
| --- | --- |
| 01-no-finance-supplier.jpg | all data scope with suppliers.view and purchases.view, without finance.view: supplier paid aggregate is omitted; procurement count and 300 CNY contract aggregate remain visible. |
| 02-no-finance-purchase.jpg | Shared procurement remains visible; paid/unpaid amounts and payment tab do not appear. API omits these financial summary fields and returns no nested payment plans. |
| 03-no-orders-supplier.jpg | purchases.view without orders.view: all three shared purchase contracts remain visible, related sales order numbers are masked. API order IDs and related allocation orders are also filtered. |
| 04-no-orders-purchase.jpg | Shared purchase workbench has no visible related sales order allocation rows. |
| 05-self-supplier-sales-scope.jpg | self account sees its own F-SO-0 association, while same-department other salesperson and cross-department customer associations are hidden. All three shared purchases remain visible. |
| 06-all-supplier-authorized.jpg | Fully authorized all account sees the 300 CNY procurement aggregate and 20 CNY paid aggregate. |
| 07-all-purchase-finance.jpg | Authorized procurement workflow: plan and paid/unpaid values remain available, 100 / 20 / 80 CNY. |
| 08-no-orders-purchase-list-normal.jpg | Final optional-reference repair: no unauthorized orders request or misleading reference load warning; shared procurement list is usable and sales identifiers are masked. |

## Scope and outstanding items

Supplier Context now carries the server user. All PurchaseOrderSerializer / SupplierSerializer nested API call sites inspected in this repair carry request/user identity. Missing identity fails closed under RBAC, with the existing server-owned development access unchanged. Procurement contract data remains shared; finance plans, financial aggregates, and sales identifiers follow their required module permissions and Data Scope. JSON regressions exercise actual response fields rather than frontend-only hiding.

No model migration, ledger/balance changes, allocation writes or procurement flow redesign. Previous business decision item remains: historical sales ledger records that have lost every ownership relationship require business verification; no guessed migration.

B2-B was not started. Await independent ChatGPT review.
