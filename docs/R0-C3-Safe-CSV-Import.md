# R0-C3 — Safe CSV Import

Baseline: `015e09a83d3e17859a99469b57261bc02eb0ca7b`.

## API contract

- `POST /api/import/csv/preview/` accepts `entity` and a CSV `file`. It returns `total`, `created`, `updated`, `errors`, and a 30-minute `preview_token` only when there are no errors.
- `POST /api/import/csv/execute/` accepts the same entity and file plus `preview_token`. The token is bound to the entity and SHA-256 of the exact uploaded file.
- Legacy `POST /api/import/csv/` is preview-only and cannot write data.

Focused repair: the signed token also binds each business key to its preview action and, for existing records, its ID, `updated_at`, and a stable hash of concrete field values. Execute compares this state before validation and again under row locks before writing. Changed state returns “数据状态已发生变化，请重新预览后再导入。” without importing any rows. The existing frontend error path clears the preview result and token; an interaction test verifies that a new preview is required.

Focused regression covers create becoming update, modified Customer/Product/SKU targets (including bulk changes without a timestamp update), duplicate Transaction creation, and unchanged updates. All 12 safe-import backend tests and the frontend conflict interaction test pass.

CSV accepts UTF-8/BOM, up to 5,000 data rows. Empty files, missing required headers, duplicate in-file business keys and unsupported Orders are rejected. Preview simulates the existing serializer/service write path within a rolled-back transaction. Execute simulates once again, then writes the complete file in one transaction.

## Validation

Focused backend tests cover preview zero writes, invalid rows, duplicate keys, same-file tokens, invalid/expired tokens, atomic execute rollback, empty/header/row-limit guards, duplicate transaction numbers and Orders prohibition. Existing import tests now use preview then execute. The complete backend suite reports 608 passing tests (10 existing skips); the frontend Node suite reports 115 passing tests, and the production build succeeds.

Chrome Use UAT covered valid preview, invalid preview with no-write wording, the custom execution confirmation, and a completed import of two dedicated UAT customers. Evidence is stored only on the `ux-review-evidence` branch under `ux-review/r0-c3-safe-import/`.
