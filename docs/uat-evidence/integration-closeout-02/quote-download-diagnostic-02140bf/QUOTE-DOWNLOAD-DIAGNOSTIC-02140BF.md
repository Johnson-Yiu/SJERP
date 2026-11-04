# Quote export quiet-timing diagnostic — 02140bf

Candidate: 02140bf46df27ba1abf5b9018507c07aae825769. Runs used the isolated test runner, synthetic SQLite/MEDIA_ROOT and a dedicated Chrome context. No canonical product source, Git ref, or CI configuration was changed. The copied Playwright test retained its original actions and assertions; only diagnostic hooks were added in the disposable checkout.

## Result

Initial attempts 01–03 produced one cancellation and two successful downloads. Follow-up attempt 04, run after the internal path clue, passed. Attempt 05 was not run.

| Attempt | Result | Browser evidence |
|---|---|---|
| 01 | Playwright failed at download.saveAs: canceled | Export HTTP 200; Blob 10,216 bytes; connected anchor clicked while userActivation.isActive=true; download started then canceled about 115 ms later. URL revocation had not occurred. No dialog event was observed. |
| 02 | 1/1 passed | Export HTTP 200; download finished with no failure. CDP dialog observer saw no dialog. |
| 03 | 1/1 passed | Export HTTP 200; download finished with no failure. Chrome 156.0.8078.80; CDP dialog observer saw no dialog. |
| 04 | 1/1 passed | Using the full frozen evidenceRoot, runtime worker 0 reported downloadsPath length 232; download.path() returned a 269-character internal file path. Export HTTP 200; no failure. Chrome 156.0.8078.80. |

For attempt 01, the parent-read timing sequence was: route to quote detail at 16.258; export response 200 at 16.400; URL.createObjectURL at 16.411; connected anchor click at 16.412; download start at 16.418; cancellation at 16.533. The route change preceded the export response. There was no navigation after the click before cancellation. This does not support attributing the cancellation to the 1-second URL revoke, a post-click route transition, expired activation at click time, or a dialog dismissal.

## beforeunload and dialog observations

Attempt 01 recorded two beforeunload events before export. Both had defaultPrevented=false and empty-string returnValue; the later event preceded the export response by about 1.06 seconds. No page.on(dialog) event was recorded. The attempt-01 hook had a dialog listener that would call dismiss(), and its dialogPolicy text incorrectly described that as Playwright’s default for every dialog. Since no dialog event occurred, that handler did not run in this attempt; the policy description is not evidence of a dialog disposition.

Attempts 02 and 03 removed the dialog listener and observed CDP Page.javascriptDialogOpening/Closed only. No Page.handleJavaScriptDialog call was made, and no dialog event was observed. Their beforeunload samples also had defaultPrevented=false. No browser dialog or beforeunload event was observed at the cancellation point because those attempts passed.

## Actual saveAs target-path length

From each run’s actual isolated database path and the observed suggested filename, the test’s saveAs destination was 84 characters: C:\Users\Johnson\AppData\Local\Temp\sunjack-r1-repair-06-KTmTtE\SJ20261104DE002.xlsx on attempt 01. Attempts 02 and 03 also measured 84 characters (their unique isolated root names differ). The copied test constructs it as path.join(ISOLATED_TEST_ROOT, download.suggestedFilename()).

This measures the test’s saveAs target only. Chrome/Playwright’s internal temporary download path was not recorded, so its length remains UNKNOWN; this short target does not establish the cancellation cause or rule out a separate internal-path issue.
## Cancellation-reason collection

The failure-only chrome://downloads and Browser.getHistograms({query:'Download'}) hooks were added after attempt 01. Attempts 02 and 03 passed, so neither failure-only query ran. The attempt-01 Chrome profile was cleaned by the isolated runner before those hooks existed. Therefore no interruptReason or histogram bucket was captured, and no Chromium enum value is interpreted here.

## Follow-up attempt 04: exact long-path run

Attempts 01–03 used three distinct evidenceRoot directories under the disposable diagnostic checkout; none used the full frozen evidenceRoot. Attempt 04 used the requested full path:
D:\Codex项目\森爵照明管理系统\.worktrees\r1-prelaunch-consolidation-20261104\.tmp\final-integrated-02140bf\docs\uat-evidence\integration-closeout-02\final-02140bf-frontend

At runtime, Playwright reported workerIndex 0, outputDir length 208, artifactsDir/downloadsPath length 232, and download.path() returned this 269-character file path:
D:\Codex项目\森爵照明管理系统\.worktrees\r1-prelaunch-consolidation-20261104\.tmp\final-integrated-02140bf\docs\uat-evidence\integration-closeout-02\final-02140bf-frontend\artifacts\d2b7026b-edea-4d2f-9176-b97889b47224\.playwright-artifacts-0\74b6d287-10b5-49fb-a59e-8c5cd49667d8

That run passed 1/1, export returned HTTP 200, and download.failure() was null. This proves the 269-character path succeeded in this run; it does not prove that the path length caused or did not cause the earlier cancellation. The test’s 84-character saveAs destination is tracked separately and is not used as counterevidence to the internal path. Because attempt 04 passed, failure-only chrome://downloads and Browser.getHistograms were not queried; interruptReason remains UNKNOWN.

Attempt 04 wrote diagnostic-only output under the frozen candidate evidenceRoot. It is supplemental evidence, not part of the original full browser run or its 262-pass/1-fail tally. The added paths are:
- artifacts/d2b7026b-edea-4d2f-9176-b97889b47224/.last-run.json
- browser/quote-download-diagnostic-attempt-04/{fixture.json,browser-results.json,chrome-quote-actions-320.png,chrome-quote-actions-390.png,chrome-quote-actions-1024.png,chrome-quote-actions-1440.png}

These files were left in place and will not be counted as the original run’s screenshots or artifacts. No attempt 05 was started; the long-path run passed and the coordinating agent stopped further diagnostic attempts after this inconclusive successful control.
## Evidence and log history

- Timelines and per-attempt artifacts are indexed in artifact-manifest.json.
- Attempts 01–03 each have four Chrome screenshots (320, 390, 1024, 1440 px); attempts 02–03 also have browser-results.json.
- Attempts 02 and 03 raw runner logs remain under the diagnostic checkout’s ignored .tmp\private-raw-logs; their separate published logs are redacted copies. The raw log paths and SHA-256 values are in each run-metadata.json.
- Evidence scan found zero token-shaped token fields in published artifacts.

Attempt-01 log preservation incident: I redacted the then-current runner.log in place. This overwrote the old published bytes. The parent supplied the prior fingerprint: 16,771 bytes, SHA-256 f6808e701cfb269fc95e37b0f47d4dc442829e53c7808d51006218ac3df69fb9. Those bytes are not recoverable from this worktree, and the original raw source path is UNKNOWN/not retained. The current sanitized replacement is 16,729 bytes, SHA-256 7d7cc18590f66be18726eaa7c00d0568fa2379cfae40efd111d874f1f8fb7cc3; log-version-audit.json records both fingerprints and this limitation. This is not represented as preservation of the old log.

The runner allocated API/Vite ports 8319/8320, 8809/8810, and 9047/9048 by binding free local ports and rechecking availability; each run log confirms its owned process trees stopped and both ports were released. No unknown service was contacted or stopped.

The frozen candidate HEAD remained the requested SHA. The canonical API, browser spec, and runner paths remain clean. Attempt 04 added only the separately listed diagnostic evidence under the ignored frozen evidence subtree; no product source, Git ref, CI config, or original full-suite result was changed.
