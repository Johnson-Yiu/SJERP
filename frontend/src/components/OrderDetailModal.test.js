import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./OrderDetailModal.vue', import.meta.url)

test('order workbench exposes retained contract amount adjustments', async () => {
  const source = await readFile(componentUrl, 'utf8')
  assert.match(source, /ContractAmountAdjustments/)
  assert.match(source, /contract-type="order"/)
})

test('order workbench exposes shipment history and reversal flow', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /发货记录/)
  assert.match(source, /shipments\/\$\{shipmentReversalTarget\.value\.id\}\/reverse/)
  assert.match(source, /shipmentReversalTarget\.has_overage/)
  assert.match(source, /该发货单包含超发\/增补。冲销会同步撤销系统生成的增补订单明细；客户追加产生的未收款应收计划也会取消。如已发生收款，系统将拒绝冲销。/)
  assert.match(source, /<button v-if="shipment\.status === 'confirmed'" class="text-btn" @click="openShipmentReversal\(shipment\)">冲销<\/button>/)
  assert.doesNotMatch(source, /暂不能直接冲销/)
  assert.match(source, /已冲销/)
  assert.match(source, /shipmentReversalReason/)
})

test('batch over-shipment requires a line-specific reason and one explicit batch warning before submitting', async () => {
  const source = await readFile(componentUrl, 'utf8')
  const submitSection = source.slice(source.indexOf('async function submitShipment()'), source.indexOf('function openShipmentReversal'))

  assert.match(submitSection, /baseQuantity\(line\) > Number\(line\.unshipped_quantity\)/)
  assert.match(submitSection, /每条超发明细都必须分别选择超发原因。/)
  assert.match(submitSection, /message: shipmentOverageSummary\(overageShipmentLines\.value\)/)
  assert.match(submitSection, /overage_reason: baseQuantity\(line\) > Number\(line\.unshipped_quantity\) \? line\.overage_reason : ''/)
  assert.match(submitSection, /confirmDialog/)
  assert.match(submitSection, /shipmentSaving\.value = true/)
  assert.match(submitSection, /catch \(err\) \{ shipmentError\.value = shipmentErrorMessage\(err\) \}/)
  assert.match(submitSection, /api\.post\(`\/orders\/\$\{props\.id\}\/ship\//)
})

test('order workbench exposes explicit packing plan generation and snapshot display', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /\['packing', '装箱'\]/)
  assert.match(source, /尚未生成预计装箱方案/)
  assert.match(source, /生成预计装箱方案/)
  assert.match(source, /重新生成预计装箱方案/)
  assert.match(source, /重新生成会使用当前 SKU 包装配置，并替换当前订单的预计装箱方案。/)
  assert.match(source, /total_cartons/)
  assert.match(source, /total_net_weight/)
  assert.match(source, /total_gross_weight/)
  assert.match(source, /total_cbm/)
  assert.match(source, /packaging_template_snapshot/)
  assert.match(source, /qty_per_carton_snapshot/)
  assert.match(source, /requires_confirmation/)
  assert.match(source, /packingPlan\.warnings/)
})

test('packing plan loading never generates a plan implicitly', async () => {
  const source = await readFile(componentUrl, 'utf8')
  const loadSection = source.slice(source.indexOf('async function load()'), source.indexOf('async function loadOperationLogs'))

  assert.match(source, /const packingSaving = ref\(false\)/)
  assert.match(source, /async function generatePackingPlan\(\) \{\s+if \(packingSaving\.value\) return\s+packingSaving\.value = true/)
  assert.match(source, /finally \{ packingSaving\.value = false \}/)
  assert.match(source, /async function regeneratePackingPlan\(\) \{\s+if \(packingSaving\.value\) return/)
  assert.equal([...source.matchAll(/:disabled="packingSaving"/g)].length, 2)
  assert.match(loadSection, /api\.get\(`\/orders\/\$\{props\.id\}\/packing-plan\//)
  assert.doesNotMatch(loadSection, /api\.post\(/)
  assert.match(source, /confirmDialog\(\{ title: '确认重新生成'/)
})

test('order workbench exposes procurement shortage, draft coverage, generation and linked purchases', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /procurement-plan/)
  assert.match(source, /生成采购草稿/)
  assert.match(source, /待采购/)
  assert.match(source, /采购草稿/)
  assert.match(source, /draft_procurement_quantity/)
  assert.match(source, /draftable_quantity/)
  assert.match(source, /关联采购单/)
  assert.match(source, /ProcurementDraftModal/)
})
