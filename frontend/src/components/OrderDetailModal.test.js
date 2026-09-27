import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./OrderDetailModal.vue', import.meta.url)

test('order workbench exposes shipment history and reversal flow', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /发货记录/)
  assert.match(source, /shipments\/\$\{shipmentReversalTarget\.value\.id\}\/reverse/)
  assert.match(source, /shipment\.has_overage/)
  assert.match(source, /包含超发\/增补，暂不能直接冲销/)
  assert.match(source, /已冲销/)
  assert.match(source, /shipmentReversalReason/)
})

test('order workbench exposes explicit packing plan generation and snapshot display', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /\['packing', '预计装箱'\]/)
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
  assert.match(source, /window\.confirm\('重新生成会使用当前 SKU 包装配置，并替换当前订单的预计装箱方案。'/)
})
