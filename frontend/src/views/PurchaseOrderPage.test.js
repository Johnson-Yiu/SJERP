import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./PurchaseOrderPage.vue', import.meta.url)

test('purchase desk exposes retained contract amount adjustment history', async () => {
  const source = await readFile(componentUrl, 'utf8')
  assert.match(source, /PurchaseDetailModal/)
  const detail = await readFile(new URL('../components/PurchaseDetailModal.vue', import.meta.url), 'utf8')
  assert.match(detail, /contract-type="purchase_order"/)
})

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

  const detail = await readFile(new URL('../components/PurchaseDetailModal.vue', import.meta.url), 'utf8')
  assert.match(detail, /item\.receipts/)
  assert.match(source, /receipts\/\$\{reversalTarget\.value\.receipt\.id\}\/reverse/)
  assert.match(source, /冲销采购入库/)
  assert.match(detail, /已冲销/)
  assert.match(source, /reversalReason/)
})

test('purchase desk labels ordered, received, remaining and overage quantities separately', async () => {
  const source = await readFile(new URL('../components/PurchaseDetailModal.vue', import.meta.url), 'utf8')

  assert.match(source, /下单 \{\{ item\.trade_quantity \?\? item\.quantity \}\}/)
  assert.match(source, /已到 \{\{ item\.received_quantity \}\}/)
  assert.match(source, /剩余 \{\{ item\.remaining_quantity \}\}/)
  assert.match(source, /item\.overage_quantity/)
  assert.match(source, /receipt\.overage_summary/)
})

test('purchase desk keeps drafts editable and separates placement from draft save', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /function editDraft\(row\)/)
  assert.match(source, /api\.put\(`\/purchase-orders\/\$\{editingPurchaseId\.value\}\//)
  const detail = await readFile(new URL('../components/PurchaseDetailModal.vue', import.meta.url), 'utf8')
  assert.match(detail, /编辑草稿/)
  assert.match(detail, /确认下单/)
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

test('missing supplier source is described as optional without implying automatic creation', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /未维护供应商供货档案，本次采购仍可继续。/)
  assert.doesNotMatch(source, /保存采购单时建立此供应商的供货档案/)
})

test('purchase price reference only carries across matching currencies and resets stale prices', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /source\.currency !== draft\.value\.currency/)
  assert.match(source, /item\.unit_price = ''/)
  assert.match(source, /切换采购币种将清除当前采购价格。原价格不会自动换汇/)
  assert.match(source, /await confirmDialog/)
  assert.match(source, /更换供应商将清除当前商品的供应商来源/)
  assert.match(source, /supplierPriceWarning\(item\)/)
  assert.match(source, /参考价未自动带入，请填写本次实际采购单价/)
  assert.match(source, /source\.purchase_price \}\} \{\{ source\.currency/)
})

test('cost allocation loads minimal cross-order candidates through procurement permission', async () => {
  const source = await readFile(componentUrl, 'utf8')
  const modal = await readFile(new URL('../components/PurchaseCostAllocationModal.vue', import.meta.url), 'utf8')

  assert.match(source, /function openCostAllocation\(purchase\)/)
  assert.match(source, /api\.get\('\/purchase-orders\/cost-allocation-orders\/'\)/)
  assert.match(source, /:orders="costOrders"/)
  assert.match(source, /@allocate-cost="openCostAllocation"/)
  assert.match(modal, /row\.sales_link_restricted && !form\.can_edit/)
  assert.match(modal, /\{\{ order\.order_no \}\}/)
  assert.doesNotMatch(modal, /order\.customer_name/)
})
