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

test('purchase editor exposes a read-only SKU inventory reference without changing procurement values', async () => {
  const source = await readFile(componentUrl, 'utf8')
  const reference = await readFile(new URL('../components/PurchaseSkuReference.vue', import.meta.url), 'utf8')

  assert.match(source, /PurchaseSkuReference/)
  assert.match(source, /切换上方 SKU 可查看库存参考/)
  assert.match(reference, /仅供采购判断；不自动分配库存、不改采购数量/)
  assert.match(reference, /actual_quantity/)
  assert.match(reference, /reserved_quantity/)
  assert.match(reference, /available_quantity/)
  assert.match(reference, /in_transit_quantity/)
  assert.match(reference, /\/skus\/\$\{id\}\//)
  assert.match(reference, /\/skus\/\$\{id\}\/versions\//)
  assert.match(reference, /当前账号无库存查看权限，库存数量不在采购页面显示。/)
  assert.match(reference, /未显示库存数量，采购仍可继续。/)
  assert.match(reference, /库存详情/)
})

test('narrow SKU picker keeps a usable scroll area and falls back after canceling the active SKU', async () => {
  const source = await readFile(new URL('../components/SkuPickerPanel.vue', import.meta.url), 'utf8')

  assert.match(source, /height:auto;min-height:var\(--sku-picker-height\)/)
  assert.match(source, /min-height:160px;max-height:260px;overflow-y:auto/)
  assert.match(source, /next\.includes\(id\) \? id : \(next\.at\(-1\) \|\| ''\)/)
})

test('inventory reference exposes recorded movement and supplier-difference context without inventing batch versions', async () => {
  const source = await readFile(new URL('../components/PurchaseSkuReference.vue', import.meta.url), 'utf8')

  assert.match(source, /inventory-detail/)
  assert.match(source, /查看库存记录与差异/)
  assert.match(source, /存放地点/)
  assert.match(source, /供应来源/)
  assert.match(source, /仓库是该流水登记地点，不等同当前分仓余额/)
  assert.match(source, /不代表库存批次版本/)
  assert.match(source, /source_label/)
  assert.match(source, /历史采购来源未记录/)
})
