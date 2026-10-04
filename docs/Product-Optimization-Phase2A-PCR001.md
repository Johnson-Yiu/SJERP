# SUNJACK-ERP — Product Optimization Phase 2A / PCR-001

Updated: 2026-10-05  
Scope: PCR-001 only. PCR-002 and Phase 2B are not started.

## Acceptance status

**PCR-001: PASS.** The order list retains its local search and list instance while a detail query opens or changes. Create/edit query actions now synchronize the configured prefill fields. The production modal navigation guard is shared with route lifecycle tests and preserves browser history behavior.

The six required UI acceptance cases below passed against the running Vite frontend and Django SQLite development data. No business form was saved during UAT.

## Remediation

- `frontend/src/views/DocumentPage.vue`: Orders listen only to `customer` and `quote` as create-prefill fields; Quotes listen only to `customer`. Updating one of those fields while `create=1` reinitializes the route-controlled modal. Unrelated query changes do not reset a manually opened modal.
- `frontend/src/views/ResourcePage.vue`: create-prefill query keys come from `props.config.fields`. The watcher resynchronizes an open route-controlled create modal when one of those keys changes, and ignores prefill changes when a manual modal is open or an edit modal is active.
- `frontend/src/utils/modalNavigation.js`: exports `installModalNavigationGuard(router)`; production routing and memory-router lifecycle tests install the same guard.
- `frontend/src/router.js`: delegates guard installation to the shared helper. Modal redirects retain the initiating push/replace history mode. Same-page create routes do not receive an unnecessary `returnTo`; close therefore clears action fields without a self-redirect. Explicit cross-page `returnTo` is retained and restored on close.
- `frontend/tests/route-lifecycle.spec.js`: exercises the production guard, create prefill changes, manually opened modal isolation, origin/context restoration, Back/Forward, and direct modal URLs without an invented predecessor.

## UI UAT evidence

Tested in the actual browser at `http://127.0.0.1:5192` against the local application and its existing SQLite records. The UI flows were observed in the rendered pages and modals; no API or test substitute was used for these six UI cases.

| Case | UI actions and observed result | Status |
|---|---|---|
| UAT-P2A-001 | On `/orders`, search `SO-2026-00026`: one result. Open detail 26, then close it. The search value, one-row result, and filtered list remained visible. | PASS |
| UAT-P2A-002 | Open `/orders?detail=26` directly and refresh. The order workbench reloaded with heading `SO-2026-00026`. | PASS |
| UAT-P2A-003 | From the filtered order list, open detail 4 after detail 26. Browser Back restored detail 26; Forward restored detail 4. The search value remained `SO-2026-00004`. | PASS |
| UAT-P2A-004 | Rendered both customer/quote prefill combinations in Orders (`customer=1,quote=1` then `customer=2,quote=5`); Quotes with customers 1 and 2; Purchase Orders with `supplier=1` and `order=26`; SKUs with `product=1`; and FollowUps with `customer=1&contact=1`. Selected records matched each URL. The same-instance A→B transition and unchanged list/search DOM were also asserted through the production App and DocumentPage route-lifecycle test. | PASS |
| UAT-P2A-005 | From customer 1 detail with `status=customer`, open its FollowUp detail, click Edit, and observe `/follow-ups?edit=2&returnTo=...`. Browser Back returned to the customer detail; Forward reopened the edit modal. Cancel returned to the customer detail with `status` and `detail` preserved and no stale `edit` or `returnTo`. | PASS |
| UAT-P2A-006 | Use sidebar navigation `/quotes` → `/orders` → `/purchase-orders`. Each destination opened its own list with no inherited modal action/query or stale search state. | PASS |

### UAT-P2A-004 prefill records

- Orders: customer 1 `UAT-R1 客户 Alpha GmbH` + quote 1 `SJ20260930DE001`; customer 2 `UAT-R1 CSV Test Customer` + quote 5 `SJ20260930DE004`.
- Quotes: customers 1 and 2.
- Purchase Orders: supplier 1 `UAT 供应商 A`; order 26 `SO-2026-00026`.
- SKUs: product 1 `UAT-R1 智能面板灯`.
- FollowUps: customer 1 `UAT-R1 客户 Alpha GmbH` and contact 1 `UAT 联系人 Alpha` were selected from the route query.
- No create/edit form was submitted during the prefill checks.

The browser UAT used direct URLs for route-prefill entry points that have no visible same-page navigation control. The A→B no-remount assertion is specifically covered in `route-lifecycle.spec.js`, where the actual App, DocumentPage, and production route guard run together; that test checks the same input and table DOM nodes across the query transition.

## Automated verification

| Check | Result |
|---|---|
| Frontend Node unit suite (`npm run test:unit`) | PASS — 109 tests |
| Typography Node test (`node --test tests/detail-drawer-typography.spec.js`) | PASS — 1 test |
| Frontend Vitest suite (CI command, including route lifecycle) | PASS — 67 tests across 11 files |
| Production frontend build (`npm run build`) | PASS — Vite reports the existing >500 kB main-chunk advisory |
| Django system check | PASS — no issues |
| Django migration check (`makemigrations --check --dry-run`) | PASS — no changes detected |
| Django SQLite test suite | PASS — 472 tests, 10 skipped by project configuration |
| PostgreSQL CI | Runs on the pushed commit; record its result in the final handoff. |

## Scope and data

- No backend model or business logic changes; no migration generated.
- The actual UI UAT opened and closed modals only; it did not save, delete, or alter ERP business records.
- PCR-002 and Phase 2B remain out of scope.

## Final review

PCR-001 acceptance is complete for this remediation. The Phase 1 audit remains in `Product-Completion-Review-Phase1.md`; this document contains the current PCR-001 remediation and evidence.
