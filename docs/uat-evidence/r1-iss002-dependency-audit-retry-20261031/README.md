# R1-ISS002 Dependency Audit Retry

Date: 2026-10-31
Fixed baseline: `bd324a8c3fb64af245c3afcabbd4301c84f7711c`
Worktree reused: `codex/r1-iss002-python312-verify-20261031`
Delivery branch: `codex/r1-iss002-dependency-audit-retry-20261031`

## Result

**BLOCKED — a current vulnerability audit could not be run.** A single connectivity
probe was made to each required registry/service. PyPI, OSV, and the npm registry
all failed with `TypeError: fetch failed`. In accordance with the task, no
network retries were made. `pip-audit` and `npm audit` were therefore not run;
`npm audit fix` was not run either.

No current vulnerability count, severity, dependency path, or advisory impact is
claimed. The historic ISS-002 report at `docs/uat-evidence/iss-002-dependency-audit/`
is not a current audit result and was not reused as one. Re-run both audits when
registry access is restored, then assess each returned advisory against its
resolved dependency path and the application code paths below.

## Connectivity evidence

The one-shot probe was recorded at `2026-10-31T10:36:17Z`:

| Service | Probe | Result |
|---|---|---|
| PyPI | `https://pypi.org/simple/pillow/` | BLOCKED — fetch failed |
| OSV | POST `https://api.osv.dev/v1/query` for Pillow 13.0.0 | BLOCKED — fetch failed |
| npm registry | `https://registry.npmjs.org/-/ping` | BLOCKED — fetch failed |

Raw response: [logs/00-network-connectivity.json](logs/00-network-connectivity.json).
Audit execution decision: [logs/03-audit-execution-status.log](logs/03-audit-execution-status.log).

## Dependency-file consistency (offline check)

The static comparison passed:

- All 9 exact-pinned direct requirements in `backend/requirements.txt` match
  the corresponding exact pins in `backend/requirements.lock`.
- `psycopg[binary]==3.3.6` is represented by `psycopg==3.3.6` and
  `psycopg-binary==3.3.6` in the lock.
- The lock contains 16 exact-pinned entries in total.
- `frontend/package.json` root `dependencies` (7 entries) and `devDependencies`
  (4 entries) exactly match the root package declarations in
  `frontend/package-lock.json`.

This checks manifest/lock consistency only. It does not prove that the locked
versions are currently free of advisories, that every artifact is trustworthy,
or that an install from the registries succeeds. Raw comparison:
[logs/01-lock-consistency.json](logs/01-lock-consistency.json).

## Pillow 13.0.0: observed application paths

The two project manifests both pin `Pillow==13.0.0`. Source inspection found
Pillow in the following current paths:

1. SKU uploads use DRF's `ProtectedImageField` (`backend/crm/serializers.py`)
   and the SKU image endpoint (`backend/crm/views.py`). A requested SKU
   thumbnail calls `thumbnail_response` in
   `backend/crm/services/sku_images.py`, which opens the stored image with
   `PIL.Image.open`, selects the first frame, resizes to 84×84, applies EXIF
   orientation, converts to RGBA, and encodes WebP. Decode failures including
   `DecompressionBombError` become an unavailable-image response. Thumbnail
   responses are marked private/no-store; generated content is cached server
   side for 24 hours by image revision.
2. Quote creation copies the stored SKU image into an immutable quote-item
   image snapshot (`backend/crm/quote_snapshots.py`). Quote XLSX generation
   passes the snapshot path to `openpyxl.drawing.image.Image` in
   `backend/crm/quote_xlsx_renderer.py`.
3. Packing List XLSX generation passes a SKU image path to
   `openpyxl.drawing.image.Image` in
   `backend/crm/services/packing_list.py`.

These establish that image decoding/encoding is in active user-facing flows,
not just test code. The API's default permission class is
`crm.permissions.ModuleActionPermission` (`backend/config/settings.py`).
The audit could not determine whether any currently applicable Pillow advisory
affects these paths, because the advisory databases were unreachable. No
exploitability or severity conclusion is made.

Source references: [logs/02-pillow-source-references.log](logs/02-pillow-source-references.log).

## Vulnerability matrix

| Ecosystem / lock | Severity and advisory IDs | Dependency path | Actual impact assessment | Status |
|---|---|---|---|---|
| Python / `backend/requirements.lock` | Not determined | Not determined by current pip-audit | Pillow is used in SKU thumbnail processing and image-backed spreadsheet exports; impact depends on advisories and their vulnerable code paths | **BLOCKED** |
| JavaScript / `frontend/package-lock.json` | Not determined | Not determined by current npm audit | Current dependency/advisory graph was not queried; do not infer zero findings from missing output | **BLOCKED** |

No dependency versions or product code were changed in this retry. The prior
CPython 3.12 runtime and test evidence remains at
`docs/uat-evidence/r1-iss002-python312-verify-20261031/`; it does not substitute
for the blocked current audit.

## Evidence index

- `logs/00-network-connectivity.json` — complete one-shot endpoint results.
- `logs/01-lock-consistency.json` — raw offline manifest/lock comparison.
- `logs/02-pillow-source-references.log` — source locations for image paths.
- `logs/03-audit-execution-status.log` — why audit commands were not run.

No CI, dependency fix, merge, PR, or deployment was triggered.
