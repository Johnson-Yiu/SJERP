# R0-D4B2-A Finance Scope UI Evidence

- Main commit: 2a9d6cded67ffb4691f3741ea35ee712ce1f9d42
- Base: 3d5d2907a05b27adcb2ef66c4c7594aa284583b1
- CI: https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/38204292443
- Backend: SUCCESS, 669 tests (10 existing SQLite skips).
- Backend PostgreSQL: SUCCESS, 669 tests.
- Frontend: SUCCESS (121 Node tests, 49 Vitest files / 488 tests, production build).
- Browser: Codex built-in Chromium browser, real UI and isolated Django session accounts.
- Fixture: 4 customers across self, same department, child department, another department; shared supplier payment and public expense. Production/development personnel access configuration unchanged.

| Screenshot | Verification |
| --- | --- |
| 01-self-ledger.jpg | Final self ledger: own customer receipt + public expense + shared procurement expenses. Form reference data loads normally. After the UI payment, income 10 / expense 17. |
| 02-self-finance.jpg | Before the UI payment: self income 10 / expense 7 / net 3, own receivable 100 and shared payable 100. |
| 03-self-receivables.jpg | self: only customer A, 1 plan, 100. |
| 04-shared-payables.jpg | Shared purchase plan remains visible to all, paid 10 / remaining 90. |
| 05-shared-payment-success.jpg | Real UI self account records shared procurement payment of 10; remaining balance becomes 90. |
| 06-department-receivables.jpg | department: customers A + B, 2 plans, 200. |
| 07-department-tree-receivables.jpg | department_tree: A + B + child department, 3 plans, 300. |
| 08-all-receivables.jpg | all: all 4 customer plans, 400. |
| 09-all-finance-export.jpg | Actual server CSV downloaded through UI; totals income 40 / expense 17 / net 23 match the page. Downloaded CSV was verified locally; CSV is not uploaded. |
| 10-all-without-module-denied.jpg | With explicit user approval, isolated all account transactions.view was temporarily disabled: UI shows 403 and hides ledger navigation. Permission restored immediately and verified in database. |
| 11-self-foreign-order-denied.jpg | Direct URL to other customer's related sales order cannot open its workbench; list retains only customer A. |

No screenshots contain production data. The test database is confined to the isolated worktree. Intermediate loading/error captures were replaced after the corresponding fix and successful reload.

Business decision BLOCKED: historical sales-kind ledger rows with no customer/order/plan linkage cannot be assigned to a salesperson reliably. Restricted scopes cannot read them; authorized all-scope staff retain access. Restoring ownership or reclassifying them as public overhead requires business verification. No guessed ownership migration or changes to recorded balances/snapshots.

R0-D4B2-B not started. Await independent ChatGPT review.

