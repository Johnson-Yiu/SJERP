# Quotation Template Revamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Deliver template-accurate PI quotation creation, on-demand preview, revision-safe quotation versions, SKU pictures, and Excel export.

**Architecture:** Django owns quote identifiers, immutable revision history, snapshots, media uploads, and the export endpoint. Vue separates quotation editing from a reusable PI preview dialog. A Node spreadsheet worker imports the supplied Excel template with @oai/artifact-tool, expands product rows, fills dynamic cells, applies Arial, and writes the .xlsx returned by Django.

**Tech Stack:** Django 5.2, Django REST Framework, SQLite, Vue 3, Vite, Axios, @oai/artifact-tool Node worker.

## Global Constraints

- Keep all non-red template content unchanged; Tax ID remains blank.
- New root quote number is SJYYYYMMDDCCNNN. Each revision is SJYYYYMMDDCCNNN-n, n = 1 through 99.
- For every revision, backend quote_no, PI Invoice No., and exported filename must use the same complete SJYYYYMMDDCCNNN-n identifier.
- Editing a saved quote creates a new revision and never overwrites the prior quote.
- Exported workbook fonts are Arial throughout; PI, buyer/seller, line-table, and bank headings are Arial bold.
- Use @oai/artifact-tool for workbook authoring. Do not introduce openpyxl, xlsxwriter, or another workbook-writing package.
- Keep baseline commit 5cb5519 and make one Git commit after each task.

---

## File Structure

- backend/crm/models.py: PI snapshot, revision relation, item description, SKU image.
- backend/crm/quote_numbers.py: country-code and sequence allocation helpers.
- backend/crm/quote_export.py: canonical PI payload and Node worker invocation.
- backend/crm/serializers.py and views.py: immutable create/revise, PI data, image upload, export.
- backend/crm/migrations/0011_quote_pi_fields_and_sku_image.py: schema migration.
- backend/crm/tests/test_quotes.py: focused unit/API/export regression suite.
- scripts/generate_quote_xlsx.mjs: template importer, row expander, formatter, exporter.
- frontend/src/components/QuoteEditorModal.vue: editor and revision save.
- frontend/src/components/QuotePreviewModal.vue: presentation-only PI modal.
- frontend/src/views/DocumentPage.vue: quote integration while retaining current order flow.
- frontend/src/views/SKUPage.vue: image management.
- frontend/src/api.js and frontend/src/styles.css: blob download and shared UI styling.

### Task 1: Create PI snapshot, SKU image, and revision data model

**Files:**
- Modify: backend/crm/models.py
- Create: backend/crm/quote_numbers.py
- Create: backend/crm/migrations/0011_quote_pi_fields_and_sku_image.py
- Create: backend/crm/tests/test_quotes.py

**Interfaces:**
- Produces allocate_root_quote_no(quote_date: date, country: str) -> str.
- Produces allocate_revision_quote_no(root_quote: Quote) -> tuple[str, int].
- Adds Quote.root_quote, revision_no, recipient_name, buyer_address, buyer_email, buyer_phone, lead_time_days, deposit_ratio, trading_terms, shipping_details; QuoteItem.description; SKU.image.

- [ ] Step 1: Write failing tests for root and revision identifiers.

~~~python
def test_root_number_uses_date_country_and_sequence(self):
    quote = create_quote(country="Germany", quote_date=date(2026, 8, 15))
    self.assertEqual(quote.quote_no, "SJ20260815DE001")

def test_revision_number_keeps_complete_root_identifier(self):
    root = create_quote(country="Germany", quote_date=date(2026, 8, 15))
    revision = create_revision(root)
    self.assertEqual(revision.quote_no, "SJ20260815DE001-1")
    self.assertEqual(revision.root_quote_id, root.id)
~~~

- [ ] Step 2: Run cd backend; python manage.py test crm.tests.test_quotes.QuoteRevisionTests -v 2. Expected: FAIL because models/helpers do not exist.

- [ ] Step 3: Implement models and transactional allocation. Use transaction.atomic and select_for_update for same-day sequence and each root's revision counter. Local ISO mapping resolves country names and returns a validation error for an unsupported country. SKU image uses upload_to="sku-images/%Y/%m/".

- [ ] Step 4: Run cd backend; python manage.py makemigrations crm; python manage.py migrate; python manage.py test crm.tests.test_quotes.QuoteRevisionTests -v 2. Expected: migration applied and tests PASS, including -99 maximum validation.

- [ ] Step 5: Commit.

~~~bash
git add backend/crm/models.py backend/crm/quote_numbers.py backend/crm/migrations/0011_quote_pi_fields_and_sku_image.py backend/crm/tests/test_quotes.py
git commit -m "feat: add quote PI snapshots and revisions"
~~~

### Task 2: Expose create, revise, PI payload, and image APIs

**Files:**
- Modify: backend/crm/serializers.py
- Modify: backend/crm/views.py
- Modify: backend/crm/urls.py
- Modify: backend/config/settings.py
- Modify: backend/config/urls.py
- Modify: backend/crm/tests/test_quotes.py

**Interfaces:**
- Produces POST /api/quotes/ for root quotes, POST /api/quotes/{id}/revise/ for new versions, GET /api/quotes/{id}/pi-data/, and POST /api/skus/{id}/image/.
- pi-data returns invoice_no, buyer snapshot, terms, totals, payment splits, product descriptions, and image URLs.

- [ ] Step 1: Write failing API tests.

~~~python
def test_create_populates_contact_snapshot(self):
    response = self.client.post("/api/quotes/", root_quote_payload(self.customer), format="json")
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    self.assertEqual(response.data["recipient_name"], "Primary Contact")

def test_revise_creates_not_updates_and_returns_full_invoice_no(self):
    root = create_quote()
    response = self.client.post(f"/api/quotes/{root.id}/revise/", revised_payload(), format="json")
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    self.assertEqual(response.data["quote_no"], f"{root.quote_no}-1")
~~~

- [ ] Step 2: Run cd backend; python manage.py test crm.tests.test_quotes.QuoteApiTests -v 2. Expected: FAIL because actions and fields are absent.

- [ ] Step 3: Implement QuoteSerializer.create to allocate a root number and populate snapshots when absent. Add revise action to copy prior quote/items, validate new values, allocate revision number, and create a new row. Return 400 for PUT/PATCH with “已保存报价请创建迭代版本”. Configure MEDIA_URL, MEDIA_ROOT, development media serving, image MIME validation, and image URL serialization.

- [ ] Step 4: Run cd backend; python manage.py test crm.tests.test_quotes.QuoteApiTests -v 2. Expected: PASS for snapshot, immutable historical version, pi-data, and image upload validation.

- [ ] Step 5: Commit.

~~~bash
git add backend/crm/serializers.py backend/crm/views.py backend/crm/urls.py backend/config/settings.py backend/config/urls.py backend/crm/tests/test_quotes.py
git commit -m "feat: expose quote revision and SKU image APIs"
~~~

### Task 3: Generate template-based PI Excel files

**Files:**
- Create: scripts/generate_quote_xlsx.mjs
- Create: backend/crm/quote_export.py
- Modify: backend/crm/views.py
- Modify: backend/crm/tests/test_quotes.py

**Interfaces:**
- Produces GET /api/quotes/{id}/export/ with attachment filename <complete quote_no>.xlsx.
- Worker CLI: node scripts/generate_quote_xlsx.mjs --input-json <payload.json> --output-xlsx <path>.

- [ ] Step 1: Write failing export tests.

~~~python
def test_export_filename_and_invoice_use_full_revision_identifier(self):
    revision = create_revision(create_quote())
    response = self.client.get(f"/api/quotes/{revision.id}/export/")
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertIn(f"{revision.quote_no}.xlsx", response["Content-Disposition"])
    self.assertTrue(response.content.startswith(b"PK"))

def test_export_two_items_contains_sku_codes_and_arial_style(self):
    response = self.client.get(f"/api/quotes/{self.multi_item_quote.id}/export/")
    self.assertIn(b"SKU-002", unzip_member(response.content, "xl/worksheets/sheet1.xml"))
    self.assertIn(b"Arial", unzip_member(response.content, "xl/styles.xml"))
~~~

- [ ] Step 2: Run cd backend; python manage.py test crm.tests.test_quotes.QuoteExportTests -v 2. Expected: FAIL because export is absent.

- [ ] Step 3: Implement build_pi_export_payload(quote) in quote_export.py. It calculates totals, deposit/balance, validity days, and English amount words once. It uses a temporary directory, fixed worker path, JSON-safe input, controlled subprocess execution, cleanup in finally, and QuoteExportError.

- [ ] Step 4: Implement the Node worker using FileBlob and SpreadsheetFile. Import the PI template; copy/insert product-row formatting for every additional item; shift totals/notes/bank block; insert images when present; write red-marked dynamic cells; apply Arial to all used cells and bold Arial to title/header cells; inspect key ranges, render once, then export.

- [ ] Step 5: Add the export viewset action. Return 422 if generation fails without changing the saved quote.

- [ ] Step 6: Run cd backend; python manage.py test crm.tests.test_quotes.QuoteExportTests -v 2. Then render a generated workbook and verify Arial, bold headers, full -n invoice identifier, multi-item layout, and fixed seller/bank sections. Expected: PASS.

- [ ] Step 7: Commit.

~~~bash
git add scripts/generate_quote_xlsx.mjs backend/crm/quote_export.py backend/crm/views.py backend/crm/tests/test_quotes.py
git commit -m "feat: export template-based PI workbooks"
~~~

### Task 4: Build on-demand quote preview and editor

**Files:**
- Create: frontend/src/components/QuoteEditorModal.vue
- Create: frontend/src/components/QuotePreviewModal.vue
- Modify: frontend/src/views/DocumentPage.vue
- Modify: frontend/src/api.js
- Modify: frontend/src/styles.css

**Interfaces:**
- QuoteEditorModal receives quote, customers, skus, and mode create|revise; it emits close and saved.
- QuotePreviewModal receives an unsaved normalized draft and emits close.
- downloadQuoteExport(id, quoteNo) obtains /quotes/<id>/export/ as a blob.

- [ ] Step 1: Add a manual acceptance checklist: editor has no preview pane; Preview opens a separate child modal with unsaved data; closing preview retains inputs; saving existing quote creates -n; save/export downloads the complete identifier.

- [ ] Step 2: Run cd frontend; npm run build. Expected: PASS, while the old all-in-one quote form does not satisfy the checklist.

- [ ] Step 3: Extract quote-only behavior from DocumentPage into QuoteEditorModal; leave existing order editing unchanged. Draft state includes buyer snapshots, PI terms, products, totals, and payment splits. Preview button opens QuotePreviewModal without saving.

- [ ] Step 4: Build QuotePreviewModal as the PI hierarchy: title; buyer/seller bands; invoice/date; dynamic product lines; totals; amount words; notes; immutable bank block. Use template copy and show an empty image frame when a URL is missing.

- [ ] Step 5: For new drafts post to /quotes/. For saved quotes post to /quotes/{id}/revise/. Disable manual quote number changes. After a successful save, download export and refresh the list; if download fails, offer re-export for the newly saved quote.

- [ ] Step 6: Run cd frontend; npm run build. Browser-check: preview is not embedded in the editor, changing quantity changes next preview, and saved quote creates a new -1 row while the source remains unchanged. Expected: PASS.

- [ ] Step 7: Commit.

~~~bash
git add frontend/src/components/QuoteEditorModal.vue frontend/src/components/QuotePreviewModal.vue frontend/src/views/DocumentPage.vue frontend/src/api.js frontend/src/styles.css
git commit -m "feat: add on-demand PI quote preview"
~~~

### Task 5: Add SKU image management UI

**Files:**
- Modify: frontend/src/views/SKUPage.vue
- Modify: frontend/src/styles.css

**Interfaces:**
- Consumes SKU image upload endpoint and serialized image URL.
- Produces picker/clear controls and thumbnail in SKU list and edit dialog.

- [ ] Step 1: Add a manual acceptance checklist: selected file previews before upload, only images submit, refreshed list shows thumbnail, clear state saves, and selected quote SKU passes its image URL to PI preview.

- [ ] Step 2: Run cd frontend; npm run build. Expected: PASS, while current SKU UI lacks images.

- [ ] Step 3: Add a hidden image input with accept="image/*", object URL preview, FormData upload after SKU creation, Image list column, and clear action. Revoke object URLs on replacement/unmount and surface server validation errors in existing toast.

- [ ] Step 4: Run cd frontend; npm run build. Browser-check PNG/JPEG upload, persisted thumbnail after reopen, and same image in quote preview. Expected: PASS.

- [ ] Step 5: Commit.

~~~bash
git add frontend/src/views/SKUPage.vue frontend/src/styles.css
git commit -m "feat: manage SKU images for PI quotations"
~~~

### Task 6: Regression verification and documentation

**Files:**
- Modify: backend/crm/tests/test_quotes.py
- Modify: README.md

- [ ] Step 1: Add tests for empty image, USD/CNY/EUR/GBP headers, shipping/discount math, 40% deposit, validity-day calculation, unsupported country, unchanged root after -2, and exact filename/Invoice No. equality for -1 and -2.

- [ ] Step 2: Run cd backend; python manage.py test -v 2. Expected: all existing and quote tests PASS.

- [ ] Step 3: Run cd frontend; npm run build. Expected: PASS with no unresolved imports.

- [ ] Step 4: Create a root quote and two revisions. For -2 use two SKUs (one without image), shipping, discount, 40% deposit, and non-default terms. Check history, modal preview, full -2 identifier in PI and filename, and template layout without overlap.

- [ ] Step 5: Update README with image upload, revision behavior, export setup, and filename convention. Commit.

~~~bash
git add backend/crm/tests/test_quotes.py README.md
git commit -m "test: verify quotation PI workflow"
git status --short
~~~

Expected: clean worktree after all tests and build pass.

## Plan Self-Review

- Spec coverage: Tasks 1–2 cover snapshots, image API, country code numbering, and immutable revisions. Task 3 covers dynamic template export, typography, and aligned identifiers. Task 4 implements editor and on-demand preview. Task 5 supplies image maintenance. Task 6 validates all required scenarios.
- Placeholder scan: no unresolved placeholder or unscoped implementation phrase remains.
- Type consistency: quote_no, root_quote, revision_no, pi-data, revise, export, and image use the same names in every task.
