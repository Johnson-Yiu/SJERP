import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'vitest'
import path from 'node:path'

const source = async (file) => readFile(path.resolve(process.cwd(), 'src', file), 'utf8')

test('sales copy names the draft, revision, PI and sales-order transitions explicitly', async () => {
  const [documentPage, quoteEditor, quoteDetail, quotePreview, orderDraft] = await Promise.all([
    source('views/DocumentPage.vue'),
    source('components/QuoteEditorModal.vue'),
    source('components/QuoteDetailModal.vue'),
    source('components/QuotePreviewModal.vue'),
    source('components/OrderDraftModal.vue'),
  ])

  assert.match(documentPage, /管理销售订单、履约与回款。/)
  assert.match(documentPage, /保存后为草稿；确认订单后进入履约。/)
  assert.match(documentPage, /保存销售订单草稿/)
  assert.match(quoteEditor, /创建报价修订版/)
  assert.match(quoteEditor, /报价单草稿/)
  assert.match(quoteEditor, /保存报价/)
  assert.match(quoteDetail, /标记为客户已接受/)
  assert.match(quoteDetail, /当前报价不能转单，请先创建修订版。/)
  assert.match(quotePreview, /PI 预览/)
  assert.match(orderDraft, /销售订单草稿/)
  assert.match(orderDraft, /确认订单后才会预留库存并生成应收计划。/)
})

test('purchase copy keeps MOQ as an exception path and preserves multi-order allocation wording', async () => {
  const [purchasePage, picker, purchaseDetail, purchaseOverview] = await Promise.all([
    source('views/PurchaseOrderPage.vue'),
    source('components/PurchaseSupplierPicker.vue'),
    source('components/PurchaseDetailModal.vue'),
    source('utils/purchaseOverview.js'),
  ])

  assert.match(purchasePage, /本次采购有明细低于供应商 MOQ。/)
  assert.match(purchasePage, /填写例外原因后仍可下单；取消则保留当前采购草稿。/)
  assert.match(purchasePage, /一张采购单可关联多个销售订单，具体归属在成本分配中处理。/)
  assert.match(purchasePage, /保存采购草稿不会生成应付或在途采购；确认采购下单后才进入正式采购流程。/)
  assert.match(purchasePage, /确认采购下单后将生成应付计划并进入在途采购。/)
  assert.match(purchaseOverview, /action: '确认采购下单'/)
  assert.match(picker, /选择采购来源/)
  assert.match(picker, /会修改整张采购单的供应商/)
  assert.match(purchaseDetail, /确认采购下单/)
  assert.match(purchaseDetail, /交易主体快照/)
  assert.match(purchaseDetail, /后续供应商主档修改不会覆盖/)
  assert.doesNotMatch(purchasePage, /payment_terms_config/)
})

test('fulfillment copy distinguishes real Packing List records from estimated packing', async () => {
  const packing = await source('components/ShipmentActualPacking.vue')
  const orderDetail = await source('components/OrderDetailModal.vue')

  assert.match(packing, /实际装箱（Packing List）/)
  assert.match(packing, /不会改变预计装箱、发货、库存或订单数量。/)
  assert.match(packing, /保存实际装箱/)
  assert.match(orderDetail, /整单冲销会同步撤销关联的超发或增补记录。/)
  assert.match(orderDetail, /商品信息按保存时的快照显示。/)
})
