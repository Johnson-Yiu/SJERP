# History workflow root cause and harness correction

## Scope and current status

This is a focused investigation of the history takeover Chrome workflow against the frozen integrated checkout `447d7816ead2e971e249cb2e762b1a6f7009b9c0`. The r01, r02, and r03 result files and original logs remain unchanged. The corrected harness was then run once on the parent-frozen integrated checkout `02140bf46df27ba1abf5b9018507c07aae825769`; all five Chrome stages and the corrected read-only verification passed. See [the final 02140bf report](final-02140bf-history-chrome/FINAL-HISTORY-CHROME-02140BF.md). No product file, Git ref, CI workflow, or PostgreSQL environment was changed or used by this work.

The r03 browser scenarios all passed, but its original read-only verifier failed on an incorrect model-field assumption. A corrected verifier passed against a copy of the sanitized r03 database and media. The later unified frozen run is recorded separately in the linked 02140bf report.

## r02 workflow failure

The failure was in the synthetic acceptance fixture, not the integrated product workflow. The preserved [r02 Chrome log](final-447d-history-chrome-r02/logs/history-operational-workflow.log) shows `selectOption` timing out at the delivered workflow script's account selector. The script requested `合成验收账户 (UAT-HISTORY-CNY)`. The frozen UI renders each account option as `{{ item.name }} ({{ item.code }})` at `.tmp/final-integrated-447d/frontend/src/views/HistoryTakeoverPage.vue:418`. The r02 seed had already included the code in the account name, so its actual option text duplicated the code. The r02 sanitized database confirms the account existed, was active, owned, and CNY, and the API log records `GET /api/finance-ledger/` as HTTP 200; this was not a missing account, API, or permission failure.

The docs-only seed now names the synthetic account `合成验收账户`, leaving the UI to append the code once. The delivered workflow script and its assertions were not edited. With that fixture correction, r03 workflow passed. Because r02 workflow failed, the runner correctly did not attempt dependent fulfillment; its verifier then failed because receipt/shipment idempotency records did not exist. That verifier error is downstream of the failed prerequisite, not a second product defect.

## Other preserved failures and corrections

| Run | Preserved result | Root cause | Correction and current evidence |
| --- | --- | --- | --- |
| r01 | `synthetic-api-seed` exit 1; no Chrome launched | Django `APIClient` used host `testserver`, rejected by the isolated runtime's `ALLOWED_HOSTS` while creating the synthetic category. | The docs seed sends `HTTP_HOST=127.0.0.1`. r02 and r03 seeding passed. Original log: `final-447d-history-chrome/logs/synthetic-api-seed.log`. |
| r02 | workflow exit 1; fulfillment blocked; verifier exit 1 | Account option label duplicated the code as described above. Fulfillment was correctly withheld after its prerequisite failed. | Account fixture corrected only. r03 workflow and fulfillment both passed. Original workflow and verifier logs are retained under `final-447d-history-chrome-r02/logs/`. |
| r03 | five Chrome scripts passed; original verifier exit 1 | The verifier queried optional legacy `GoodsReceipt.request_key` / `Shipment.request_key` fields. The service stores request keys in `FulfillmentIdempotency`; its response payload carries the linked record id. | The docs-only verifier now checks the two idempotency rows, operation/status/target, follows each response payload id to the receipt/shipment, and retains the exact quantity checks. The original failed verifier log remains `final-447d-history-chrome-r03/logs/read-only-business-verification.log`; the corrected copy verification is PASS in `final-447d-history-chrome-r03/corrected-verification-final.json` and its linked log. |
| Corrected-verifier helper attempt | Helper exit 1 before launching Python | Node `copyFile` was passed an options object where the API expects a numeric mode. | The docs-only helper now copies into a fresh marked isolated directory and then invokes the read-only verifier. The helper failure remains in `final-447d-history-chrome-r03/logs/verify-published-helper-failure.log`; the later corrected run passed. |

## r03 browser and data evidence

On Chrome `156.0.8078.80`, r03 passed the operational review/execution, workflow, fulfillment, inventory-location, and template-download scripts (5/5, zero browser failures). The workflow exercised synthetic history archive and execution, two cash facts with separate synthetic sessions, an inventory baseline, itemized balances, and confirmed continuation drafts. Fulfillment posted a 3-unit receipt and 6-unit shipment, replayed both requests with `Idempotent-Replay: true`, and ended with receivable 40 and payable 6. The read-only verifier found 2 succeeded idempotency records, 2 finance facts, 1 baseline, 2 inventory movements, 2 continuation contracts, 16 history events, and 21 operation-log rows.

The run retained eight desktop/narrow screenshots and the actual downloaded workbook. The inventory acceptance copy differs from the frozen source only in its Playwright import path and substitution of the API-generated SKU `SKU-000001` for the source fixture `UAT-HT-S1`; all UI actions and expectations remain. The original source script was not changed.

The verifier was rerun read-only against a fresh isolated copy of the published sanitized database and media. It passed with exit code 0. The published database has 102 tables; only the two `django_session` rows were removed from the copy. All non-session business/audit table contents remained unchanged (1,091 rows; manifest SHA-256 `218a77ad143664b8752bcb8d7ebf1ec21a86dacf1196d528923d11fc6e18d393`). The copied voucher bytes match the stored 55-byte digest. The original application DB was not modified. Temporary verification files were removed through the owned-root marker guard.

All actors in this synthetic run are development identities. The report does not treat the default development name or the two synthetic browser sessions as real employee authentication or acceptance.

## Acceptance harness changes

- `seed_integrated_history_uat.py`: corrected isolated API host handling and account display-name fixture; it still creates business records through the formal API/services and guards the isolated runtime.
- `verify_integrated_history_uat.py`: corrected the idempotency-to-record lookup using the service response payload; it retains the assertions for operation, status, target, receipt quantity, and shipment quantity.
- `verify_published_history_uat.mjs`: runs the verifier on a separately marked copy of the published DB/media and preserves its exit status/log.
- `run-integrated-history-uat.mjs`: orchestrates the isolated run and preserves each stage result; a failed prerequisite continues to block dependent fulfillment.
- `history-inventory-location-chrome-uat-447d-r03.mjs`: temporary docs acceptance copy only; two mechanical fixture/import substitutions, no expectation removal.

No history product defect was established by the r02/r03 workflow failures, so no product code was changed. The corrected harness completed its single rerun on `02140bf46df27ba1abf5b9018507c07aae825769`. All five Chrome scenarios, live verification, sanitized-copy verification, artifact checks, and cleanup passed. The r01–r03 failures remain preserved as separate original evidence.

## Evidence paths

- Original run records: `final-447d-history-chrome/result.json`, `final-447d-history-chrome-r02/result.json`, `final-447d-history-chrome-r03/result.json`.
- r03 corrected verifier record: `final-447d-history-chrome-r03/corrected-verification-final.json`.
- Machine-readable root cause and script/evidence hashes: `history-workflow-root-cause-447d.json`.
