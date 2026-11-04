# Final history Chrome UAT — 02140bf

## Result

**PASS** on frozen integrated checkout `02140bf46df27ba1abf5b9018507c07aae825769` at `.tmp/final-integrated-02140bf`. The FINAL runner exited 0. All five explicit Chrome stages passed, both live and corrected-copy read-only business verification exited 0, and the result JSON records no failures or blocked stages.

The preflight and post-run checks recorded the exact requested HEAD and clean `backend/` and `frontend/` directories. Direct Django API identity, Vite identity, and the Vite-proxied API identity all matched the isolated SQLite and media paths. Ports 53621/53622 were released, the marked application temp root and marked verification-copy root were cleaned, and the frozen application directories remained clean.

## Stage results

| Stage | Result | Duration |
| --- | --- | ---: |
| Isolated migrations | PASS | 61.472 s |
| Synthetic API seed | PASS | 10.420 s |
| Operational review/execution Chrome | PASS | 22.517 s |
| History workflow Chrome | PASS | 29.279 s |
| Fulfillment Chrome | PASS | 13.965 s |
| Inventory-location Chrome | PASS | 11.090 s |
| Template-download Chrome | PASS | 8.097 s |
| Live read-only business verification | PASS | 1.067 s |
| Sanitized database copy | PASS | 1.161 s |
| Corrected read-only verification of copied DB/media | PASS | 1.055 s |

Chrome version was `156.0.8078.80`. The actual local HTTP log contains 98 API requests: 90 responses with status 200 and 8 with status 201. API/Vite identity probes and proxied API identity were also captured. The 13 published logs include raw and published SHA-256 values; two isolation-capability token occurrences were redacted from the published copies.

## Verified synthetic business state

- The history application reached `executed` with 12 source rows and 16 history events. Two development-only browser sessions performed the synthetic maker/reviewer flow; these are not real employee identities or real employee authentication acceptance.
- Finance recorded two posted facts (income 287.43 and expense 35.00 CNY-account workflow facts), with a voucher file whose stored size and SHA-256 matched the copied bytes.
- One inventory baseline was posted for API-generated SKU `SKU-000001`; two inventory movements and two continuation contracts were present.
- Fulfillment posted and replayed one 3-unit receipt and one 6-unit shipment. Both replay responses were successful; ending receivable and payable were 40 and 6 respectively.
- Audit summary: 16 history events and 21 operation-log rows.

## Preserved artifacts and integrity

- The sanitized SQLite copy is `artifacts/isolated-sanitized.sqlite3`, SHA-256 `5a563ed3cd6c1d8c7e596d145338f56abaf1b21719ddb04334d3459509d4847b`. It contains 102 tables and 1,091 business/audit rows. Two `django_session` rows were removed from the published copy; business/audit table contents were unchanged. A separate read-only SQLite check returned `integrity=ok`, 102 tables, and zero session rows.
- The copied media contains one synthetic voucher at `artifacts/media/finance-vouchers/2026/11/9c8de84e55e84fda801a520583259574.pdf` (55 bytes; SHA-256 `94f673e3511b44ae4cce4189c7bf246b5106f5c0d9ed50767c58265d53c19fb9`).
- The actual downloaded workbook is `template/history-takeover-template.xlsx` (14,077 bytes; SHA-256 `791723d6644a697d8d8657018c5807a8c7de3e59a6f2fe813d41b31c50454720`).
- Eight actual Chrome screenshots are present: desktop and 390px narrow captures for operational, workflow, fulfillment, and inventory-location pages. Each image has dimensions and SHA-256 in `result.json`.
- Evidence contains no `session.json` or `reviewer-session.json`. Private session files remained in the marked system TEMP root and were removed by the owned-root cleanup guard.

## Source-script provenance

All five source scripts in the supplied checkout matched their reviewed 447d SHA-256 values and were copied byte-for-byte under `harness/source-scripts/`. The original actions and assertions were run unchanged. Only the inventory-location acceptance copy was mechanically adapted:

1. Import: `@playwright/test` → the exact installed Playwright entry in the supplied frozen checkout. Input SHA-256 `fa36c1fe2edee2b02c237e62b5d5a6d323d0f6b2e52b5589d0e1e72afc34710a`; output SHA-256 `2145a623e81016806fe54973c2805db9bf667ed8775b1caa34370b36e28559ba`.
2. API-generated SKU: `UAT-HT-S1` → `SKU-000001` (six occurrences). Input SHA-256 `2145a623e81016806fe54973c2805db9bf667ed8775b1caa34370b36e28559ba`; final copy SHA-256 `e6c3feae8332e63b9bc05e9c560bc061ee46527d479d83eb201b5d02fedf3945`.

The runner verified that reversing those two substitutions exactly reconstructs the source script. No assertion was removed or weakened.

## Evidence index

- Machine result, stage exit codes, clean checks, HTTP request summary, hashes, screenshots and transformation manifest: [`result.json`](result.json)
- Corrected read-only business summary: [`business-row-summary-corrected.json`](business-row-summary-corrected.json)
- Live read-only business summary: [`business-row-summary-live.json`](business-row-summary-live.json)
- Desktop/narrow screenshots: `operational/`, `workflow/`, `fulfillment/`, `inventory-location/`
- Actual downloaded template: [`history-takeover-template.xlsx`](template/history-takeover-template.xlsx)
- API, Vite, migration, seed, browser and verifier logs: `logs/`
- Exact source-script copies and mechanically adapted inventory script: `harness/`

The prior r01, r02 and r03 directories and their failures remain untouched. This report covers isolated synthetic history acceptance only; the displayed development identity is not a real employee, and this run did not alter product code, Git refs, CI, PostgreSQL, or real business data.
