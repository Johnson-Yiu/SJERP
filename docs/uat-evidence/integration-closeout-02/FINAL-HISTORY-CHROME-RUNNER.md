# FINAL history Chrome runner

`run-final-history-chrome.mjs` is a docs-only, no-overwrite runner for the final integrated history browser acceptance. It leaves `run-integrated-history-uat.mjs` and all r01–r03 evidence in place.

## Invocation

Pass the exact frozen worktree, full 40-character SHA, and a new direct-child evidence directory:

```powershell
node docs/uat-evidence/integration-closeout-02/run-final-history-chrome.mjs `
  --checkout "D:\Codex项目\森爵照明管理系统\.worktrees\r1-prelaunch-consolidation-20261104\.tmp\final-integrated-02140bf" `
  --sha 02140bf46df27ba1abf5b9018507c07aae825769 `
  --evidence-dir "D:\Codex项目\森爵照明管理系统\.worktrees\r1-prelaunch-consolidation-20261104\docs\uat-evidence\integration-closeout-02\final-02140bf-history-chrome"
```

The invocation completed once after the parent confirmed frontend `npm ci` exit 0. It produced `final-02140bf-history-chrome/result.json` with overall `PASS`; see [the run report](final-02140bf-history-chrome/FINAL-HISTORY-CHROME-02140BF.md). Evidence directories are exclusive: use a different new directory for any separately authorized run. This runner only checks the required local Vite/Playwright entries and never installs dependencies.

## Preflight and isolation

- Requires the supplied HEAD to equal the supplied full SHA and Git top-level to equal the supplied worktree.
- Requires `git status --porcelain --untracked-files=all -- backend frontend` to be empty before and after the run.
- Requires a new, nonexistent evidence directory directly under this report directory. It creates files exclusively and refuses overwrite.
- Requires the project Python 3.12 environment and existing candidate `frontend/node_modules`.
- Checks loopback ports 53621/53622 are free before use and again after stopping only the API/Vite process trees started by this run.
- Uses the existing `.sunjack-playwright-isolation.json` marker, `test_support.isolated_settings`, `verify_isolated_runtime`, direct API identity, Vite identity, and Vite-proxied API identity checks. The database and media stay under a fresh system TEMP root; only a sanitized DB copy and synthetic media are published.
- Keeps browser session JSON under the marked TEMP root and checks that no session JSON enters evidence. Publishes logs with only the isolation capability token redacted and records raw/published hashes and replacement counts.

## Browser scripts and copy provenance

The runner checks all five source scripts against their reviewed 447d SHA-256 values and explicit Chrome launch marker, copies the original source bytes into the new evidence directory, and executes the source scripts unchanged except for the inventory-location case. That case runs from a recorded docs/evidence copy with exactly two mechanical changes: its Playwright import resolves to the candidate checkout's installed package, and hard-coded `UAT-HT-S1` is replaced by the SKU returned by the isolated API seed. The result records source, intermediate, and final copy hashes plus replacement counts and round-trip equality. No assertion or action is removed.

The stages are operational review/execution, workflow, fulfillment, inventory location, and template download. Fulfillment remains blocked if the required workflow stage fails; independent inventory and template stages still run. The corrected verifier first checks the isolated live business state, then checks the published sanitized DB/media copy in a second marker-guarded read-only temp root.

The overall `PASS` gate requires all five Chrome stages exit 0, live and corrected copy verifiers exit 0, eight screenshots, a downloaded workbook, database/media artifacts, unchanged source scripts, clean application directories, released ports, and successful owned-temp cleanup. Any mismatch stays a failure or blocked result in `result.json`.
