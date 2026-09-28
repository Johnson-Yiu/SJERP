import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./PurchaseOrderPage.vue', import.meta.url)

test('purchase desk connects creation, receipt and supplier payment actions', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /api\.post\('\/purchase-orders\/'/)
  assert.match(source, /\/receive\//)
  assert.match(source, /PurchasePaymentModal/)
  const payment = await readFile(new URL('../components/PurchasePaymentModal.vue', import.meta.url), 'utf8')
  assert.match(payment, /\/pay\//)
  assert.match(source, /\/supplier-skus\//)
  assert.match(source, /supplierSkuOptions/)
  assert.match(source, /supplier_sku/)
  assert.match(source, /新建采购单/)
  assert.match(source, /route\.query\.supplier/)
  assert.match(source, /inheritedSupplier/)
})

test('purchase desk exposes receipt history and the reversal flow', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /item\.receipts/)
  assert.match(source, /receipts\/\$\{reversalTarget\.value\.receipt\.id\}\/reverse/)
  assert.match(source, /冲销采购入库/)
  assert.match(source, /已冲销/)
  assert.match(source, /reversalReason/)
})

test('purchase desk keeps drafts editable and separates placement from draft save', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /function editDraft\(row\)/)
  assert.match(source, /api\.put\(`\/purchase-orders\/\$\{editingPurchaseId\.value\}\//)
  assert.match(source, /编辑草稿/)
  assert.match(source, /确认下单/)
  assert.match(source, /const \{ status, purchase_no, \.\.\.draftPayload \} = draft\.value/)
})

test('purchase creation leaves number generation to the backend and never submits a number', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.doesNotMatch(source, /purchaseTimeSuffix/)
  assert.doesNotMatch(source, /PO-\$\{today/)
  assert.match(source, /const \{ status, purchase_no, \.\.\.draftPayload \} = draft\.value/)
  assert.match(source, /保存后由系统自动生成/)
  assert.match(source, /class="readonly-input" readonly/)
})

test('purchase price reference only carries across matching currencies and resets stale prices', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /source\.currency !== draft\.value\.currency/)
  assert.match(source, /item\.unit_price = ''/)
  assert.match(source, /function onCurrencyChanged\(\)/)
  assert.match(source, /draft\.value\.items\.forEach\(item => \{ item\.unit_price = '';/)
  assert.match(source, /function onSupplierChanged\(\)/)
  assert.match(source, /supplierPriceWarning\(item\)/)
  assert.match(source, /参考价未自动带入，请填写本次实际采购单价/)
  assert.match(source, /source\.purchase_price \}\} \{\{ source\.currency/)
})
