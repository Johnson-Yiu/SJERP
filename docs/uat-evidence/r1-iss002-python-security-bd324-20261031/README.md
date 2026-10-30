# R1-ISS-002-SEC-01 Python dependency security re-verification

## Scope and result

- Baseline: `bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- Historical security result: `85adec7d99d725c7c920c728385172d6517730ce`
- Branch: `codex/r1-iss002-python-security-bd324-20261031`
- Verification date: 2026-10-31
- Result: **Pillow 13.0.0 and the exact-pinned Python runtime lock are consistent and install cleanly.** Requested image/Excel regressions passed. CPython 3.12 runtime verification remains outstanding because this machine has only CPython 3.14.5 available.

No Python application code or dependency versions were changed in this verification. The historical commit is not an ancestor of the fixed baseline, so its evidence was not assumed to apply automatically. Direct comparison showed `backend/requirements.txt` and `backend/requirements.lock` are byte-for-byte identical between that commit and the fixed baseline; the baseline already contains the Pillow 13.0.0 upgrade and lock.

## Dependency and Pillow path review

The baseline pins `Pillow==13.0.0` in both dependency files. `requirements.lock` also pins all transitive packages, including `Django==6.0.9`, `djangorestframework==3.18.3`, `openpyxl==3.1.5`, `psycopg==3.3.6`, and `psycopg-binary==3.3.6`. Installing the lock and dry-running `requirements.txt` produced no version conflict.

The reviewed image paths are:

| Flow | Code path and Pillow use | Regression evidence |
| --- | --- | --- |
| SKU image upload | `crm/views.py` `SKUViewSet.image`; serializer `ProtectedImageField`/DRF image validation | `crm.tests.test_quotes` |
| SKU thumbnail | `crm/services/sku_images.py`: `Image.open`, first-frame selection, `thumbnail`, EXIF transpose, RGBA conversion and WebP output | `crm.tests.test_sku_images` |
| Quote image snapshot | `crm/quote_snapshots.py` copies the selected SKU image to the immutable quote-item snapshot | `crm.tests.test_quotes`, `crm.tests.test_iss020_quote_export` |
| Quote export image | openpyxl embeds the saved snapshot; test opens the exported workbook image and verifies it | `crm.tests.test_iss020_quote_export` |
| Packing List image and XLSX | `crm/services/packing_list.py` uses `openpyxl.drawing.image.Image`, preserves template/media relationships and exports the workbook | `crm.tests.test_packing_list_export` |

The upload endpoint checks the request's declared MIME type, while the thumbnail path calls `Image.open()` without an explicit `formats=` allowlist. The declared MIME type is therefore not treated as proof that the underlying encoded format is constrained; parser-level hardening and hostile-image/resource-limit coverage remain separate review items.

Pillow's official advisory GHSA-78g4-xqwv-q3g8 describes a high-severity heap-buffer-overflow in bundled OpenJPEG reachable through `Image.open(...).load()`. Its affected range is 11.1.0–12.3.0 and its patched version is 13.0.0, so the locked version is outside the affected range. The relevant format-sniffing path makes this advisory applicable to the code-path review, but not to the installed patched version. The official Pillow 13.0.0 release notes list the security fixes included in that release.

GHSA-654x-cwwv-5j9c is also patched in 13.0.0; it requires Arrow export with `PILLOW_ALIGNMENT > 1`. The reviewed application paths do not export Arrow arrays or set that alignment option, so that particular issue is not currently applicable to these flows. The lock-wide `pip-audit` scan found no known vulnerabilities at verification time; this does not replace future advisory monitoring or platform-image scanning.

## Clean environment and test evidence

The verification used a newly created temporary CPython 3.14 virtual environment and installed the complete lock with:

```powershell
python -m venv <temporary-verification-root>\venv
<temporary-verification-root>\venv\Scripts\python.exe -m pip install --requirement backend/requirements.lock
```

The temporary runtime reported `Django 6.0.9`, `Pillow 13.0.0`, DRF `3.18.3`, and openpyxl `3.1.5`. The verification set a temporary SQLite `DATABASE_URL` and temporary `MEDIA_ROOT`; a full migration was applied only to that temporary database. Django's test runner used its isolated in-memory test database. No business database or existing media directory was used.

| Check | Result |
| --- | --- |
| `pip install -r backend/requirements.lock` in a clean virtual environment | PASS |
| `pip check` | PASS — no broken requirements |
| `pip install --dry-run -r requirements.txt` from `backend/` against the locked environment | PASS — all direct and transitive requirements satisfied at the pinned versions |
| `python manage.py check` | PASS — no issues |
| `python manage.py makemigrations --check --dry-run` | PASS — no changes detected |
| `python manage.py migrate --noinput` against temporary SQLite | PASS — migrations through `crm.0092` applied |
| `pip-audit --requirement requirements.lock --no-deps --disable-pip` from `backend/` | PASS — no known vulnerabilities found; exact pins were audited, while the audit tool's own environment and pip were excluded |
| `crm.tests.test_sku_images crm.tests.test_quotes crm.tests.test_iss020_quote_export crm.tests.test_packing_list_export` | PASS — 104 tests, 0 failures, 58.825 seconds |

The 104 tests include SKU image upload/clear and thumbnail behavior, saved quote image snapshots and exports, and Packing List image embedding and workbook export. Expected 400/422 responses are asserted by tests and did not represent suite failures.

## Python 3.12 limitation and residual risks

`py -0p` listed only `C:\Python314\python.exe` (Python 3.14.5); the common Python 3.12 installation locations checked were absent. Thus no claim is made that this was a Python 3.12 runtime test. Re-run the clean install, `pip check`, Django/migration checks, and the image regression set under actual CPython 3.12 before treating that runtime target as verified.

The lock is exact-pinned but does not include wheel hashes. `pip-audit` warned that pinned dependencies should also be hash-locked. Production image/library inventory, production database/backend, hostile image corpus, and deployment resource limits were not exercised here. No `npm audit fix`, application-code change, database-schema change, or shared-ledger edit was made.

## References

- [Pillow GHSA-78g4-xqwv-q3g8](https://github.com/python-pillow/Pillow/security/advisories/GHSA-78g4-xqwv-q3g8)
- [Pillow GHSA-654x-cwwv-5j9c](https://github.com/python-pillow/Pillow/security/advisories/GHSA-654x-cwwv-5j9c)
- [Pillow 13.0.0 security release notes](https://github.com/python-pillow/Pillow/blob/main/docs/releasenotes/13.0.0.rst)
- [Pillow official security advisories](https://github.com/python-pillow/Pillow/security/advisories)
