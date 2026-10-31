# R1-ISS-052 oversized CSV HTTP 413 verification

Date: 2026-10-31
Branch: `codex/r1-iss052-http-413-bd324-20261031`
Base: `codex/r1-iss052-csv-limit-bd324-20261030` at `d08ca625ac6beeec51ecc14eb92c97da0ea6f63b`

## Result

**PASS — isolated local HTTP, Chrome, and relevant regression checks.** The CSV size-limit upload handler now raises `StopUpload(connection_reset=False)`. Django can finish parsing the request by discarding unread input in bounded 16 KiB chunks, close any open upload files, and let the endpoint return its explicit HTTP 413 response. The over-limit chunk is not forwarded to memory/disk upload handlers.

This is not a production or reverse-proxy acceptance. No production database, PostgreSQL service, deployed proxy, or real business data was used. The final branch SHA is provided with the delivery.

## HTTP coverage and resource checks

A real loopback HTTP test through Django's live test server sent a 327,699-byte CSV (multipart bodies 327,956–328,054 bytes) against the 64 KiB test limit through every backend CSV upload route:

| Route | HTTP result | Temporary files after response | Imported customers / row audits |
|---|---:|---:|---:|
| `POST /api/import/csv/preview/` | 413 | 0 | 0 / 0 |
| `POST /api/import/csv/execute/` | 413 | 0 | 0 / 0 |
| `POST /api/import/csv/` | 413 | 0 | 0 / 0 |

The execute endpoint records only a failed import batch with no file digest and zero processed/failed rows. The HTTP client successfully read the 413 body for all three requests; the test fails on a socket close/reset instead. Exact responses and post-request resource/database observations are in `http-413-all-upload-routes.json` inside [the raw log archive](logs.zip).

The existing streaming-limit regression also asserts that processing stops before the oversized body is fully read by the CSV upload handlers: bytes forwarded stay at or below the configured 64-byte test limit, the memory upload handler is not activated, no uploaded file reaches the view, and CSV parsing is not invoked. Django's parser exhausts the unread request stream in 16 KiB chunks so it can keep the HTTP connection and return 413; this does not accumulate the remainder as an application buffer or create an upload temp file. This verifies bounded application-side buffering and cleanup, not a process-wide memory profile.

## Real Chrome evidence

Playwright used the installed Chrome channel (Headless Chrome 156) against the isolated Vite and Django servers and the actual import page. A 10,747,926-byte CSV exceeded the configured 10,485,760-byte limit. The browser received HTTP 413 with the size-limit response body, observed zero failed requests, and displayed the limit in the page alert.

- Test log and browser/response metadata: `chrome-csv-upload-413.log` and `chrome-csv-upload-413.json` inside [the raw log archive](logs.zip)
- Screenshot from this run: [chrome-csv-upload-413.png](screenshots/chrome-csv-upload-413.png)

The import UI exercises the preview route; all three backend upload routes are independently exercised over real HTTP above.

## Regression results

| Check | Actual result |
|---|---|
| Focused Django HTTP test | 1 passed / 0 failed |
| Relevant CSV/import/security backend regression | 117 passed / 0 failed |
| Isolated Chrome browser test | 1 passed / 0 failed |
| `npm run test:unit` | 171 passed / 0 failed / 0 skipped |
| `npm run build` | PASS |
| `git diff --check` | PASS after final documentation changes |
| `npm ci` | PASS |

The complete unmodified command outputs (including stdout, stderr, browser metadata, and the three-route HTTP measurements) are in [logs.zip](logs.zip). The archive also contains the isolated backend/frontend server logs.

Backend tests used Python 3.14.5, Django 6.0.9, DRF 3.18.3, and isolated in-memory SQLite. The focused test uses a dedicated temporary upload directory and forces disk-upload threshold to 1 KiB. The 117-test regression includes safe CSV import routes, upload limits, dashboard imports, RBAC/data-scope checks, and the customer CSV flow.

The 117-test command was:

```text
python manage.py test crm.tests.test_csv_upload_http_413 crm.tests.test_safe_csv_import crm.tests.test_dashboard_import crm.tests.test_document_numbers crm.tests.test_functional_rbac crm.tests.test_sales_data_scope crm.tests.BusinessFlowTests.test_customer_csv_import_updates_by_code --verbosity 1
```

## Warnings and remaining verification

- The production bundle still emits Vite's existing warning that the main JavaScript chunk exceeds 500 kB (1,127.97 kB uncompressed / 394.22 kB gzip).
- `npm ci` reported existing package deprecations and five moderate audit findings; dependencies were not changed as part of this fix.
- The local suite proves the Django application behavior. Request-size ceilings, buffering, timeouts, and client-visible 413 behavior at the deployed reverse proxy/load balancer remain **NEEDS VERIFICATION**. An upstream that closes oversized requests before Django handles them may behave differently.
- No migration was added. SQLite test setup applied the existing migrations; PostgreSQL migration/runtime compatibility was not tested in this task.
- No CI was triggered, no master merge or deployment occurred, and the global Issue ledger was not modified.
