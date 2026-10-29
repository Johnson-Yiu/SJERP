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
  assert.match(detail, /确认采购下单/)
  assert.match(source, /const \{ status, purchase_no, \.\.\.draftPayload \} = draft\.value/)
})

test('formal purchase history prefers the saved supplier snapshot and exposes its party details', async () => {
  const source = await readFile(componentUrl, 'utf8')
  const detail = await readFile(new URL('../components/PurchaseDetailModal.vue', import.meta.url), 'utf8')

  assert.match(source, /function supplierPartyName\(row\)/)
  assert.match(source, /row\.supplier_name_snapshot \|\| '历史主体未记录'/)
  assert.match(source, /当前主档：\$\{row\.supplier_name\}/)
  assert.match(detail, /row\.value\.supplier_name_snapshot \|\| '历史主体未记录'/)
  assert.match(detail, /交易主体快照/)
  assert.match(detail, /supplier_address_snapshot/)
})

test('order fulfillment purchase history prefers formal supplier snapshots', async () => {
  const detail = await readFile(new URL('../components/OrderDetailModal.vue', import.meta.url), 'utf8')

  assert.match(detail, /function purchasePartyName\(purchase\)/)
  assert.match(detail, /purchase\.supplier_name_snapshot \|\| '历史主体未记录'/)
  assert.match(detail, /当前主档参考：\$\{purchase\.supplier_name\}/)
  assert.doesNotMatch(detail, /<small>\{\{ purchase\.supplier_name \}\}<\/small>/)
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

test('purchase editor aggregates maintained MOQ in base units without blocking draft save', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /const moqWarnings = computed/)
  assert.match(source, /group\.actual_quantity \+= actual/)
  assert.match(source, /baseQuantity\(item\)/)
  assert.match(source, /moq-editor-warning/)
  assert.match(source, /可保存草稿；确认采购下单时需填写例外原因。/)
  assert.match(source, /供应商供货档案正在加载，暂无法判断 MOQ。/)
})

test('purchase placement keeps low MOQ as a reasoned soft exception and displays retained evidence', async () => {
  const source = await readFile(componentUrl, 'utf8')
  const detail = await readFile(new URL('../components/PurchaseDetailModal.vue', import.meta.url), 'utf8')

  assert.match(source, /purchase_moq_exception_required/)
  assert.match(source, /moq_exception_reason: reason/)
  assert.match(source, /填写原因并继续下单/)
  assert.match(detail, /purchase-moq-exception/)
  assert.match(detail, /确认时间/)
  assert.match(detail, /确认人员/)
})
