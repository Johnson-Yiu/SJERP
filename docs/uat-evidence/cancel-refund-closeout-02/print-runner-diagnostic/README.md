# Bounded existing print-runner diagnosis

2026-11-14. No production code changed. No expanded print acceptance campaign.

Integration run `5ee24175-54ad-43da-8806-ebb41cecf60e` failed native complete1440/header=false, multipage and optional-empty at the 20-second PDF existence assertion. Narrow390 exhausted the overall 150-second test budget. Native complete1440/header=true passed. Application resource-blocking and resource-ready tests passed. Two failing cases subsequently had PDFs in their short temporary output directories; no final evidence-copy or MAX_PATH error was reported.

One bounded diagnostic ran the unchanged seven assertions with only native test budget explicitly 150 seconds and PDF existence wait changed from 20 to 60 seconds. Ports 8961/8962; isolated SQLite, media, Chrome profiles and PDF outputs; run `8c7b5c5a-6f74-4977-bee9-0e8ee9ae2686`. Actual output: **6 passed, 1 failed**. The multipage case still received `[]` after 60 seconds, before any evidence copy. The remaining four native cases generated PDFs. The temporary timeout changes were reverted after the diagnostic; they are not a validated fix.

Evidence: `run.log`, original failure `artifacts/*/iss037-print-output-accept-01c89-tipage-1440px-headers-false/error-context.md`, and `print-output` screenshots, API snapshots and actual PDFs. Four native PDFs and one independent rendered PDF exist; no multipage native PDF exists. Screenshots and API responses alone do not pass this test.

Conclusion: late native-print output and execution variability are observed; long final paths do not explain the failed assertion. Multipage native printing remains unverified. Concurrent Windows/Chrome resource contention is plausible but not proven. Preserve this R07 failure rather than declare the full suite passed; further print-specific investigation is outside this bounded diagnostic.
