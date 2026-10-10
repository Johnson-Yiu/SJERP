# R0-C2 — SKU Save Integrity

Baseline: `d30bc29702cab126a177b239127ed875ba1965bc`.

## API contract

Existing POST `/api/skus/`, PUT/PATCH `/api/skus/{id}/`, and POST `/api/skus/batch-create/` accept optional write-only `packaging_profile_input`:

```json
{"packaging_template": 12, "qty_per_carton_override": 50, "unit_net_weight": 0.15}
```

The existing `packaging` response remains read-only. Omitted or null input does not change an existing profile. No packaging deletion is introduced. Nested input cannot redirect the profile to another SKU. Packaging validation reuses SKUPackagingProfileSerializer, including disabled-template binding, numeric constraints and verification reset. SKU and packaging writes, version snapshots and ordinary SKU audit writes share a transaction. Batch inputs are validated before writes; existing locked identity validation runs again during each save, so duplicate combinations still roll back the whole batch.

The editor submits packaging with the SKU request. Images remain separate; failures say the SKU was created/updated and keep saved IDs for upload-only retry. Nested packaging errors retain their concrete message through the API interceptor.

## Automated validation

- Focused backend: create/edit success and rollback, invalid third batch item, valid corresponding batch profiles, omitted/null preservation, disabled template rejection, late database failure, audit failure, reused numeric constraints and verification reset.
- Existing identity, combination, commercial identity, category/schema and image tests remain in the full suite.
- Focused frontend: single database request containing packaging for create/edit, image failure retaining retry IDs and explicit database success, nested error message through the real API interceptor.
- Full backend: 602 tests, PASS (10 PostgreSQL-only skips locally; PostgreSQL runs in CI).
- Full frontend: 44 Vitest files / 439 tests, PASS; Node unit suite 114 tests and typography test, PASS.
- Production build, Django system check, makemigrations --check --dry-run: PASS. No migration.
- Existing build chunk-size warning remains.

## Real Chrome UAT

Dedicated UAT product `UAT-R1 智能面板灯`, newly created SKU `SKU-000006` / `UATP-3650K` / 36W / 5000K. Existing test data retained.

1. With selected UAT carton and quantity 0, save returns “创建 SKU 失败：每箱数量必须大于 0。”; editor remains open. Rollback proof is automated, not inferred from screenshot.
2. Change quantity to 50, net weight 0.15 kg; create succeeds. Close/reopen confirms template and both values.
3. Change SKU detail note to `R0-C2 原子编辑验收`, carton quantity to 40 and weight to 0.2 kg. Save and reopen confirms all values together.

Screenshot branch: `ux-review-evidence` (never merged into master).
Folder: `ux-review/r0-c2-sku-save-integrity/`.

- `R0C2_01_create_with_packaging.png`: reopened successfully created SKU.
- `R0C2_02_invalid_packaging_error.png`: concrete server validation error and quantity 0.
- `R0C2_03_edit_atomic_success.png`: reopened SKU note and updated packaging.

Completed screenshots: 3/3. Missing: none. BLOCKED: none.

Scope remains SKU + SKU packaging save integrity. No R0-D or unrelated reconstruction. Final production SHA, exact-head Actions URL and evidence SHA are reported in the delivery response.
