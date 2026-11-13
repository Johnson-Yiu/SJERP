# Existing native-print test: genuine click diagnostic

2026-11-14. One bounded follow-up to `../print-runner-diagnostic`; no production changes or expanded printing campaign.

The old native test scheduled `button.click()` inside `page.evaluate`. That is a synthetic DOM event, bypasses Playwright actionability checks and does not establish genuine browser user activation. A disabled button could silently ignore it. This did not meet the current actual-operation evidence standard.

The test now locates the print button inside the PI preview dialog, checks it is enabled, starts a normal Playwright `locator.click` without `force`, and catches its promise rejection. Node polls actual native PDF output for at most 60 seconds while the browser renderer may be blocked by printing; success then awaits the click result and copies the PDF. The native case has an explicit 150-second budget. All original API and real-file assertions remain. Console, page errors, initial disabled state and preview text are recorded. No business printing implementation changed.

One isolated run on ports 8961/8962 executed only the existing multipage case using a temporary runner `--grep` selection, removed immediately afterward. SQLite, media and Chrome profile were temporary. **1 passed (53.1 seconds total)**, actual native PDF `print-output/ui-formal-multipage-1440-headers-false.pdf` is 197234 bytes. The button was initially enabled; preview text was normal; pageErrors was empty. Console retained a network-access-denied and a 404 resource message; these did not prevent the actual PDF from being produced.

This proves the real-click case passed and closes the synthetic-interaction gap in this test. It does not establish that every earlier failure had one cause, and does not replace a final integrated suite result. The earlier 6/7 failed diagnostic is retained verbatim rather than hidden.

Evidence includes `run.log`, native PDF, screenshot, API snapshot and `*-diagnostic.json`. The complete original test matrix remains selected by default; no tests or assertions are skipped or deleted.
