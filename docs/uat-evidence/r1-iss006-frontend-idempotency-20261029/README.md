# R1-ISS006 Frontend Idempotency Storage Safety

Date: 2026-10-30  
Branch: `codex/r1-iss006-frontend-idempotency-20261029`  
Source branch: `codex/fix-iss006-request-idempotency-20261029`  
Starting source SHA: `083b99d1f3be5ed6796b71f7dfd5108b2fc12b3a`
Implementation SHA: `4c51db20759730f70ba575e2db0f776a224f4d62`

## Scope and result

This change is limited to the browser request-identity helper and its purchase-receipt / order-shipment callers. It does not change the backend idempotency contract, business validation, inventory rules, or shared Issue status. ISS-006 remains `NEEDS_VERIFICATION`.

Before this change, the helper accessed `window.sessionStorage` outside its `try` block and swallowed read/write failures. A failed write therefore returned a fresh, unpersisted ID; another attempt could generate a different ID and turn an unknown-result retry into a second inventory operation.

The helper now fails closed: property access, `getItem`, `setItem`, and successful-operation cleanup are handled explicitly. It never returns a request ID before the same ID and payload fingerprint have been persisted. If a write fails, it retains that candidate in memory so a same-page retry after storage recovers uses the same candidate; the submit remains blocked until persistence succeeds. A confirmed server success followed by cleanup failure is reported distinctly as an already-completed operation. Existing receipt and shipment catch paths surface the message to the user without sending the request when key creation fails.

## Automated verification

Commands run from `frontend/`:

| Command | Result |
| --- | --- |
| `npx vitest run tests/fulfillment-idempotency.spec.js tests/order-detail-shipment-batch.spec.js tests/purchase-editor-receipt.spec.js --environment jsdom` | PASS — 3 files, 39 tests |
| `npm run test:unit` | PASS — 169 tests, 0 failures |
| `npm run build` | PASS — production bundle built; existing >500 kB chunk warning remains |

The helper regression suite covers a throwing `window.sessionStorage` getter, throwing `getItem`, repeated `setItem` failures retaining the same request ID, identical network retry, changed payload with a distinct stable ID, successful cleanup before a new operation, and cleanup failure after confirmed success. Receipt and shipment component tests verify a failed write blocks the POST and renders the explicit safety message.

The first unprivileged Vitest invocation failed before tests started with Vite `EPERM` writing `frontend/node_modules/.vite-temp/vite.config.js.timestamp-…mjs`. The same targeted command was rerun with the worktree's required local write permission and passed. This startup failure is an environment permission issue, not a test result.

## Chrome Use verification

The local Django API and Vite UI were run against an isolated temporary SQLite database and media directory under the system temp folder; no production data or server was used. Chrome Use opened the isolated purchase order and completed one normal receive through the UI. The browser showed “验货入库已完成” and the line moved from 0/6 received to 6/6. The API log recorded exactly one `POST /api/purchase-orders/1/receive/` with HTTP 201; a database check found one `GoodsReceipt` (6.00 pcs) and one linked inventory movement, with purchase status `completed`. This confirms the normal-browser success/cleanup path remains functional. A real Chrome screenshot was captured and visually reviewed in the task session; it is not stored as a repository file.

Storage failure presentation and POST blocking were verified in the two component suites. A live storage-fault injection was not performed in Chrome; the Chrome run verified the normal path, not the error state.

## Remaining verification

- The independent ISS-006 review identified separate backend audit-snapshot, parent-state concurrency, and reversal-audit transaction concerns. They are outside this frontend-scoped change and remain for separate review/fix.
- PostgreSQL concurrency verification and end-to-end browser fault injection remain unperformed.
- This report records local evidence only; it does not close ISS-006 or claim full fulfillment idempotency acceptance.
