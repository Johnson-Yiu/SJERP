# R1-FIN-P3-A evidence

All records in this directory are synthetic and isolated from business data.

- FIXTURE_SETUP: `fixture.json`, `prepare_fixture.py`, `synthetic-bank-voucher.json`, `seed_actual.py`
- REAL_UI_ACTION: Codex in-app browser checked `/finance`, `/reports?source=actual_cash...`, and `/rmb-cash-events?event=1` against Vite 5193 and Django 8103.
- REAL_API_OBSERVATION: `REAL_API_OBSERVATION-actual-rmb-cash.json` and `.log` are the actual HTTP response/status.
- DATABASE_VERIFICATION: `DATABASE_VERIFICATION-after.json` and `.log` compare legacy model SHA256 and new confirmed event rows.
- MOCKED_TEST: unit/Vitest tests use their declared fixtures; they do not replace the real API/browser evidence.
- BLOCKED: the statistical cutover date and whole-company coverage policy are not configured; ISS-121 records the required finance-owner decision.

The dashboard and event detail screenshots were captured from the isolated HTTP application at 1440/1280/1024 widths where noted. No real credentials or production data are present.
