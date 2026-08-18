# 报价工作台与重要备注 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将报价详情升级为可查看 PI、版本谱系、全链订单、转单草稿和重要备注的报价专用工作台。

**Architecture:** 新建报价专用 API 和 Vue 详情组件，避免将报价规则继续塞进通用 `EntityDetailModal`。备注以原始报价为聚合根、以创建版本为来源；订单按原始报价链查询，转单只生成前端可编辑的预填草稿，实际保存订单后再将来源报价标记为已接受。

**Tech Stack:** Django 5、Django REST Framework、SQLite/Django migrations、Vue 3、Vite、lucide-vue-next、现有 `SimpleRichTextEditor`。

**Spec:** `docs/superpowers/specs/2026-08-18-quotation-workbench-design.md`

## Global Constraints

- 报价号与版本号继续使用 `SJYYYYMMDDCCNNN-n`，不得重写已有报价。
- 已保存报价、其买方/SKU快照、PI预览和 Excel 导出保持不可变。
- 不新增第三方富文本依赖；复用 `SimpleRichTextEditor`。
- 重要备注不进入 PI 或 Excel；失效备注不可删除，正文必须显示删除线。
- 同一版本允许多张订单；订单分页按整个原始报价链聚合并显示来源版本。

---

## File structure

- `backend/crm/models.py`：定义 `QuoteImportantNote`，保存报价链、来源版本、富文本、失效状态和创建人。
- `backend/crm/migrations/0013_quoteimportantnote.py`：创建备注表和索引。
- `backend/crm/serializers.py`：备注、报价工作台、订单草稿的序列化与订单保存后的报价状态更新。
- `backend/crm/views.py`：报价工作台、订单草稿、备注创建与失效 API。
- `backend/crm/tests/test_quotes.py`：API/模型回归。
- `frontend/src/components/QuoteDetailModal.vue`：报价专用工作台和五个分页。
- `frontend/src/views/DocumentPage.vue`：报价行使用专用工作台；订单创建消费 `quote` 查询参数的预填数据。
- `frontend/src/api.js`：可复用的 PI 下载/预览请求辅助函数（若组件不直接调用 `api`）。

### Task 1: 重要备注领域模型与 API

**Files:**
- Modify: `backend/crm/models.py`
- Create: `backend/crm/migrations/0013_quoteimportantnote.py`
- Modify: `backend/crm/serializers.py`
- Modify: `backend/crm/views.py`
- Modify: `backend/crm/tests/test_quotes.py`

**Interfaces:**
- Produces `QuoteImportantNote(root_quote, source_quote, content, is_active, created_by)`。
- Produces `GET /api/quotes/{id}/important-notes/`、`POST /api/quotes/{id}/important-notes/`、`POST /api/quotes/{id}/important-notes/{note_id}/deactivate/`。
- All reads resolve `root_quote = quote.root_quote or quote` and return the full chain’s notes, newest first.

- [ ] **Step 1: Write failing API tests**

```python
def test_important_notes_are_shared_by_the_revision_chain(self):
    root = self.create_quote()
    revision = self.create_revision(root)
    created = self.client.post(f"/api/quotes/{revision.id}/important-notes/", {"content": "<p>Use 4000K.</p>"}, format="json")
    notes = self.client.get(f"/api/quotes/{root.id}/important-notes/")
    self.assertEqual(created.status_code, status.HTTP_201_CREATED)
    self.assertEqual(notes.data[0]["source_quote_no"], revision.quote_no)

def test_deactivated_note_is_retained(self):
    note = QuoteImportantNote.objects.create(root_quote=self.quote, source_quote=self.quote, content="<p>Old term</p>")
    response = self.client.post(f"/api/quotes/{self.quote.id}/important-notes/{note.id}/deactivate/")
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertFalse(response.data["is_active"])
    self.assertEqual(QuoteImportantNote.objects.count(), 1)
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `py manage.py test crm.tests.test_quotes.QuoteApiTests -v 2` from `backend/`.

Expected: FAIL because the model and routes do not exist.

- [ ] **Step 3: Implement the model, migration and serializers**

```python
class QuoteImportantNote(TimestampedModel):
    root_quote = models.ForeignKey(Quote, on_delete=models.PROTECT, related_name="important_notes")
    source_quote = models.ForeignKey(Quote, on_delete=models.PROTECT, related_name="sourced_important_notes")
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

class QuoteImportantNoteSerializer(serializers.ModelSerializer):
    source_quote_no = serializers.CharField(source="source_quote.quote_no", read_only=True)
    created_by_name = serializers.SerializerMethodField()
```

Create a migration, add model validation that `source_quote` belongs to `root_quote`, reject stripped/HTML-empty content, and sanitize with the project’s standard HTML-cleaning helper before save. The create action uses the request user only when authenticated; anonymous development mode leaves `created_by` null and returns `系统` as the creator label.

- [ ] **Step 4: Implement actions and verify focused tests pass**

Implement nested quote actions using `get_object_or_404` on notes constrained by the resolved root. The deactivate action only flips `is_active=False`; it must not delete or edit `content`.

Run: `py manage.py test crm.tests.test_quotes.QuoteApiTests -v 2`.

Expected: PASS, including shared-chain source-version and retained-deactivation assertions.

- [ ] **Step 5: Commit**

```powershell
git add backend/crm/models.py backend/crm/migrations/0013_quoteimportantnote.py backend/crm/serializers.py backend/crm/views.py backend/crm/tests/test_quotes.py
git commit -m "feat: add quotation important notes"
```

### Task 2: 报价工作台与转单 API

**Files:**
- Modify: `backend/crm/serializers.py`
- Modify: `backend/crm/views.py`
- Modify: `backend/crm/tests/test_quotes.py`

**Interfaces:**
- Produces `GET /api/quotes/{id}/workbench/` containing `quote`, `revisions`, `orders`, `important_notes` and `order_summary`.
- Produces `GET /api/quotes/{id}/order-draft/` returning a non-persisted order payload.
- `OrderSerializer.create()` marks `order.quote.status = "accepted"` only after `Order` and all `OrderItem` records are created successfully.

- [ ] **Step 1: Write failing tests for full-chain orders and prefill**

```python
def test_workbench_returns_orders_from_every_revision(self):
    root, revision = self.create_quote_with_revision()
    first = self.create_order(quote=root, order_no="SO-001")
    second = self.create_order(quote=revision, order_no="SO-002")
    response = self.client.get(f"/api/quotes/{revision.id}/workbench/")
    self.assertEqual({row["order_no"] for row in response.data["orders"]}, {first.order_no, second.order_no})
    self.assertEqual(response.data["orders"][0]["source_quote_no"], second.quote.quote_no)

def test_order_draft_copies_current_quote_and_order_save_accepts_it(self):
    draft = self.client.get(f"/api/quotes/{self.quote.id}/order-draft/")
    self.assertEqual(draft.data["items"][0]["unit_price"], "20.4000")
    saved = self.client.post("/api/orders/", draft.data, format="json")
    self.quote.refresh_from_db()
    self.assertEqual(saved.status_code, status.HTTP_201_CREATED)
    self.assertEqual(self.quote.status, "accepted")
```

- [ ] **Step 2: Run tests to verify failure**

Run: `py manage.py test crm.tests.test_quotes -v 2`.

Expected: FAIL because workbench/order-draft routes and quote acceptance do not exist.

- [ ] **Step 3: Implement deterministic workbench and draft responses**

```python
root = quote.root_quote or quote
revisions = Quote.objects.filter(models.Q(pk=root.pk) | models.Q(root_quote=root)).order_by("revision_no", "id")
orders = Order.objects.filter(quote__in=revisions).select_related("quote", "customer").prefetch_related("items__sku__product")

return Response({
    "quote": QuoteSerializer(quote).data,
    "root_quote_no": root.quote_no,
    "revisions": QuoteSerializer(revisions, many=True).data,
    "orders": OrderSerializer(orders, many=True).data,
    "important_notes": QuoteImportantNoteSerializer(root.important_notes.select_related("source_quote", "created_by"), many=True).data,
})
```

Add read-only `source_quote_no` to `OrderSerializer`. Build `order-draft` from quote snapshots/items: use `sku`, `quantity`, `unit_price`, `cost_price=sku.cost_price`, notes, customer, currency, exchange rate, shipping fee, discount, source quote id, today’s date, empty expected ship date and `draft` status. Generate no `Order` until `POST /api/orders/` succeeds. Keep `OrderSerializer.create` transactional and flip acceptance after items are bulk-created.

- [ ] **Step 4: Run tests to verify pass**

Run: `py manage.py test crm.tests.test_quotes -v 2`.

Expected: PASS; failed order validation leaves source quote status unchanged.

- [ ] **Step 5: Commit**

```powershell
git add backend/crm/serializers.py backend/crm/views.py backend/crm/tests/test_quotes.py
git commit -m "feat: expose quotation workbench and order drafts"
```

### Task 3: 报价专用详情工作台 UI

**Files:**
- Create: `frontend/src/components/QuoteDetailModal.vue`
- Modify: `frontend/src/views/DocumentPage.vue`
- Modify: `frontend/src/api.js`

**Interfaces:**
- `QuoteDetailModal` props: `{ id: Number }`; emits `close`, `revise`, `create-order`.
- It loads `GET /quotes/{id}/workbench/`; `create-order` emits the quote id only after `GET /quotes/{id}/order-draft/` succeeds.

- [ ] **Step 1: Write a failing component-level/manual acceptance checklist**

Create `frontend/src/components/QuoteDetailModal.manual-test.md` with executable cases: open a quote, inspect overview, switch all five tabs, click a lineage version, preview PI, export Excel, open a related order, and verify no “新增 SKU” action exists. Add a short import/render smoke assertion if the project has a Vue test runner; otherwise the checklist is the explicit UI regression artifact.

- [ ] **Step 2: Run the frontend build to record the baseline**

Run: `npm run build` from `frontend/`.

Expected: PASS before the component exists; use this as the baseline command.

- [ ] **Step 3: Implement the focused workbench component**

```vue
<QuoteDetailModal :id="detailId" @close="detailId = null" @revise="editFromDetail" @create-order="openOrderDraft" />
```

Replace only the quote branch in `DocumentPage`; retain `EntityDetailModal` for orders. In `QuoteDetailModal`, add tabs `overview`, `items`, `lineage`, `orders`, `notes`. The overview is a compact summary/action page; items render snapshot fields; lineage buttons load the selected quote id into the same component; orders show every root-chain order with source version and a button to preview its source PI; no generic relation-create controls are imported.

Use existing modal/drawer CSS tokens and `QuotePreviewModal` for PI. Use `downloadQuoteExport` for Excel.

- [ ] **Step 4: Verify the build and manual checklist**

Run: `npm run build` from `frontend/`.

Expected: PASS. Run the development service and execute the new checklist against a root quote with a revision; record results in the checklist.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/components/QuoteDetailModal.vue frontend/src/components/QuoteDetailModal.manual-test.md frontend/src/views/DocumentPage.vue frontend/src/api.js
git commit -m "feat: add quotation workbench detail view"
```

### Task 4: 重要备注分页与订单草稿交互

**Files:**
- Modify: `frontend/src/components/QuoteDetailModal.vue`
- Modify: `frontend/src/views/DocumentPage.vue`
- Modify: `frontend/src/components/SimpleRichTextEditor.vue` only if it lacks a public empty-content helper

**Interfaces:**
- Note create request: `POST /quotes/{id}/important-notes/ { content: string }`.
- Note deactivate request: `POST /quotes/{id}/important-notes/{noteId}/deactivate/`.
- `DocumentPage.openOrderDraft(quoteId)` fetches `/quotes/{quoteId}/order-draft/`, assigns its payload to the existing order form, and opens the order modal.

- [ ] **Step 1: Add a failing UI acceptance case**

Extend the checklist with: create rich-text note on `-1`, open the root and see the note’s `-1` source tag, deactivate it after confirmation and see a strike-through, click “转为订单”, verify prefilled values, save, and see the order in root-chain orders with its source version.

- [ ] **Step 2: Implement note UI and safe state changes**

```vue
<SimpleRichTextEditor v-model="noteContent" />
<button :disabled="isRichTextEmpty(noteContent)" @click="createNote">新增重要备注</button>
<article :class="{ 'note-inactive': !note.is_active }" v-html="note.content" />
```

Render the fixed caution text at the top of Notes. Every note shows source quote number/revision, creator and time. Do not mutate `notes` optimistically: reload workbench data after create/deactivate. On deactivate, call `window.confirm`; failure leaves the visible note unchanged and shows the API message.

- [ ] **Step 3: Implement order-draft consumption without duplicate orders**

```js
async function openOrderDraft(quoteId) {
  const response = await api.get(`/quotes/${quoteId}/order-draft/`)
  editingId.value = null
  Object.assign(form, response.data)
  open.value = true
}
```

Normalize numeric SKU/customer/quote ids to match existing form selects. No order POST happens until the user presses “保存单据”; cancelling closes the modal without persistence. After save, reload the workbench if it remains open.

- [ ] **Step 4: Verify build and manual behavior**

Run: `npm run build` from `frontend/`.

Expected: PASS. Execute every expanded manual test case with the branch service.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/components/QuoteDetailModal.vue frontend/src/components/QuoteDetailModal.manual-test.md frontend/src/views/DocumentPage.vue frontend/src/components/SimpleRichTextEditor.vue
git commit -m "feat: add quotation notes and order conversion flow"
```

### Task 5: End-to-end regression and documentation

**Files:**
- Modify: `backend/crm/tests/test_quotes.py`
- Modify: `README.md`

**Interfaces:**
- Backend suite includes model/API/export regressions; frontend production build must remain clean.

- [ ] **Step 1: Add failure-path tests**

```python
def test_invalid_order_draft_save_does_not_accept_quote(self):
    response = self.client.post("/api/orders/", {"quote": self.quote.id, "items": []}, format="json")
    self.quote.refresh_from_db()
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertNotEqual(self.quote.status, "accepted")

def test_note_from_another_quote_chain_is_not_deactivated(self):
    response = self.client.post(f"/api/quotes/{self.quote.id}/important-notes/{other_note.id}/deactivate/")
    self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

- [ ] **Step 2: Run failure tests and then the full backend suite**

Run: `py manage.py test crm.tests.test_quotes -v 2` then `py manage.py test -v 1`, from `backend/`.

Expected: all tests PASS, including real PI/XLSX regression tests.

- [ ] **Step 3: Document the daily workflow**

Update README with: open quotation → overview/PI → review chain/notes → create order draft → complete order → inspect root-chain order history. State that important notes are chain-visible, source-version-labelled and may be obsolete; they do not appear in PI/Excel.

- [ ] **Step 4: Final verification**

Run:

```powershell
py manage.py check
py manage.py makemigrations --check --dry-run
py manage.py test -v 1
npm run build
git diff --check
```

Expected: every command succeeds and `git status --short` contains no task files outside committed changes (ignore pre-existing `.superpowers/`).

- [ ] **Step 5: Commit**

```powershell
git add backend/crm/tests/test_quotes.py README.md
git commit -m "test: verify quotation workbench workflow"
```

## Plan self-review

- **Spec coverage:** Task 1 implements shared, source-labelled, rich-text, retained notes. Task 2 implements chain grouping, order prefill and accepted status. Task 3 implements workbench/tabs/PI/export/lineage. Task 4 implements notes and transfer interactions. Task 5 covers failures, full verification and user documentation.
- **Completeness scan:** every task includes concrete commands, code shape and expected outcomes.
- **Type consistency:** routes, properties and component events are specified once and reused consistently; the API uses `source_quote_no`, while UI reads the same name.
