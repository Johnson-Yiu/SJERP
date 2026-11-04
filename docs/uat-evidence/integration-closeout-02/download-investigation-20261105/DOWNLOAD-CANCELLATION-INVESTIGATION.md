# Download cancellation investigation

**Status:** targeted lifecycle fixes are stable for the unchanged original browser scenarios and ready for the parent to freeze as a candidate. No Git operation, CI run, full 9-profile rerun, PostgreSQL/SQLite suite, or print/packing-list test was performed in this follow-up.

## Findings

Both failures were browser-side Blob download lifecycle races. The API responses succeeded, while Playwright's actual download artifact was canceled under normal timing. The original tests and their assertions remain byte-for-byte unchanged.

Per the parent’s ledger de-duplication, quote lifecycle repair belongs under existing ISS-020 and finance facts CSV export under existing ISS-105. No new Issue ID or shared-ledger edit was made here.

| Scenario | Before | Cause isolated | After |
|---|---|---|---|
| Quote XLSX export | Normal-timing original scenario failed at `download.saveAs: canceled`; export API returned HTTP 200 and 10,217 bytes. Protocol logging slowed the run and the same scenario passed, showing timing sensitivity. | [api.js](/D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/frontend/src/api.js:47) removed the appended anchor immediately and revoked its Blob URL on a 0 ms timer. | Same original browser test passed 1/1 with normal timing after deferring anchor removal and URL revocation together by 1 second. The downloaded XLSX was preserved and opened with `openpyxl`. |
| Finance CSV export | Original 1440px scenario failed at `download.saveAs: canceled`; 390px passed. Both CSV API responses returned HTTP 200. | [FinanceLedgerPage.vue](/D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/frontend/src/views/FinanceLedgerPage.vue:82) clicked a detached anchor. | Same original 1440px and 390px tests passed 2/2 after attaching the anchor and deferring its removal and URL revocation together by 1 second. Original CSV content assertions passed. |

The protocol-level pre-fix reruns completed rather than reproducing the cancellation, so no canceled `Browser.downloadProgress` event is claimed. The diagnosis is supported by normal-timing pre-fix reproduction and isolated lifecycle-only A/B changes followed by normal-timing passes. The Chrome `ITaskbarList3` and Google Update registry messages in one run were non-fatal; API responses, browser downloads, and cleanup succeeded after the local fixes.

## Actual downloaded files

- Finance CSVs: [1440px CSV](/D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/docs/uat-evidence/integration-closeout-02/download-investigation-20261105/finance-after-lifecycle-fix/browser/finance-closeout/facts-1440.csv) is 387 bytes, SHA-256 `d5869c23cb442e36ac07cacf987fd89e8f3cf38c53823a6e87e3a6e839602989`; [390px CSV](/D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/docs/uat-evidence/integration-closeout-02/download-investigation-20261105/finance-after-lifecycle-fix/browser/finance-closeout/facts-390.csv) is 596 bytes, SHA-256 `008dfd8df8cab056b73588464f7a44094df73fcd776a98ee080904fc854b1880`. The unchanged test verified the generated source number and `123.45` in both files.
- Quote XLSX: [captured browser download](/D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/docs/uat-evidence/integration-closeout-02/download-investigation-20261105/quote-file-content/browser/quote-editor-mobile-actions.spec/captured-quote-export.xlsx) is 10,218 bytes, SHA-256 `33fd031633791e75443465d7fee440d96f31461f32226f9627cde601efee5e23`. Its length matches the original test's `fs.stat` result. `openpyxl` opened the workbook (`PI`, 35 rows) and verified synthetic quote `SJ20261104DE002`, line item model `R1-QA-MODEL`, quantity 1, and unit price 12.5. The original `saveAs` assertion passed. The file is byte-exact; its invoice template also contains the configured seller banking block, so keep this evidence artifact out of a code/test-only Git commit.
- The same quote scenario was also run in the real Google Chrome channel using only a temporary `test.use({ channel: 'chrome' })` override; the original spec was restored byte-for-byte. Chrome 156.0.8078.80 reported UA `HeadlessChrome/156.0.0.0`. The original assertions passed 1/1; the actual XLSX is 10,218 bytes, SHA-256 `fb77af31c5e8bbfe97a503a696a02f09f76d25c6c62990566fc358eda0c58f00`, and passed ZIP/openpyxl checks for the synthetic quote number and line item. Desktop and narrow Chrome captures: [1440px](/D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/docs/uat-evidence/integration-closeout-02/download-investigation-20261105/quote-google-chrome/browser/quote-editor-mobile-actions.spec/chrome-quote-actions-1440.png), [390px](/D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/docs/uat-evidence/integration-closeout-02/download-investigation-20261105/quote-google-chrome/browser/quote-editor-mobile-actions.spec/chrome-quote-actions-390.png), and [320px](/D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/docs/uat-evidence/integration-closeout-02/download-investigation-20261105/quote-google-chrome/browser/quote-editor-mobile-actions.spec/chrome-quote-actions-320.png). The recorded executable is `C:/Program Files/Google/Chrome/Application/chrome.exe`, version `156.0.8078.80`.

## Changed and unchanged files

Changed only in the main integration worktree:

- `frontend/src/api.js`
- `frontend/src/views/FinanceLedgerPage.vue`

No test file was changed. The original test files remain unchanged and have the same SHA-256 as the frozen 447d checkout:

- `frontend/browser-tests/quote-editor-mobile-actions.spec.js` — `06d30d0b0a0c14997471f88b67e89d94620e0d51ac5b65de24a27d5ee4811949`
- `frontend/browser-tests/finance-closeout.spec.js` — `39633f7a6c763523a52c04c3492212ee5478f8d5cfcc2a74a65cecf046491c5b`

The frozen 447d copies of `api.js` and `FinanceLedgerPage.vue` were verified to retain their pre-fix hashes. The isolation runner, Playwright config, package manifest and lockfile also matched the frozen checkout before the two main-tree changes. This is a targeted file comparison, not a whole-worktree equivalence claim.

No evidence here justifies expanding into `downloadPackingListExport`'s 0 ms cleanup or the deferred print package. It remains an unverified similar pattern, not a reproduced defect.

## Evidence and sensitive-data handling

- Machine-readable results: [download-diagnostic-results.json](/D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/docs/uat-evidence/integration-closeout-02/download-investigation-20261105/download-diagnostic-results.json).
- The large raw protocol logs remain under the ignored local `.tmp/download-investigation-20261105/` directory; the JSON records their SHA-256 values. Published evidence contains only the summarized download facts.
- The original finance debug log is preserved byte-for-byte under local `.tmp`; only the published copy had four closed isolation-token values redacted. Source/published hashes are in [PUBLISHED-REDACTION-AUDIT.json](/D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/docs/uat-evidence/integration-closeout-02/download-investigation-20261105/finance-1440-390/PUBLISHED-REDACTION-AUDIT.json).
- In the final frontend350 evidence, 46 closed isolation-token values were redacted from 19 published text files. The original manifest remains byte-exact at SHA-256 `d108b50f4e6643ccf1c371274426030deedc83acc11ced6887860b4cfd119c30`; PNGs and source artifacts were not edited. Details are in [its redaction audit](/D:/Codex项目/森爵照明管理系统/.worktrees/r1-prelaunch-consolidation-20261104/docs/uat-evidence/integration-closeout-02/final-447d-frontend/PUBLISHED-REDACTION-AUDIT.json).
- The published diagnostic text scan found no Cookie, Set-Cookie, bearer authorization, session/CSRF cookie, or seed-credential values. All 9 isolated diagnostic temp roots were removed; no temp root remains. The final frontend350 manifest lists 350 files; all 199 PNGs still match the source byte-for-byte. The only 19 published hash differences are the audited log redactions.

## npm ci audit warnings

The two preserved npm-cache debug logs show `npm ci` exit 0, two deprecation warnings, and an audit summary of 4 moderate vulnerabilities. The recorded advisory responses identify `glob@10.5.0` (GHSA-3g3m-2fjr-6pw4) and `minimatch@9.0.9` (GHSA-g3hv-75wg-m249). Npm recommends replacing deprecated `lucide-vue-next@1.0.0` with `@lucide/vue`. The two audit snapshots assign different internal IDs to the same minimatch GHSA; this report preserves both ranges and notes that no fresh audit was run.

## Parent's next run

The two main-tree source files and their unchanged browser scenarios are ready for a new frozen candidate. The parent can freeze the exact code/test SHA, then run the complete frontend, PostgreSQL and SQLite validation once and rerun the historical Chrome evidence against that same candidate. This targeted report does not claim those final candidate runs.
