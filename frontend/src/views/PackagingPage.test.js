import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./PackagingPage.vue', import.meta.url)

test('packaging list labels physical dimensions and tare weight with their units', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /label:'长 \(cm\)'/)
  assert.match(source, /label:'宽 \(cm\)'/)
  assert.match(source, /label:'高 \(cm\)'/)
  assert.match(source, /label:'外箱皮重 \(kg\)'/)
})

test('packaging page presents tail-goods policies and no mixed-pack setting', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /尾货策略/)
  assert.match(source, /不同策略的区别/)
  assert.doesNotMatch(source, /mixed_pack_allowed|允许混装|散箱策略/)
})

test('packaging form keeps dimensions in one row and shows policy help as a floating panel', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /class="dimensions-row full"/)
  assert.match(source, /grid-template-columns:repeat\(3,minmax\(0,1fr\)\)/)
  assert.match(source, /\.policy-help\{position:absolute/)
  assert.match(source, /carton_tare_weight" type="number" min="0" step="0\.1"/)
  assert.match(source, /carton_length" type="number" min="0\.1" step="0\.1"/)
  assert.match(source, /Number\(x\.carton_length \|\| 0\)\.toFixed\(1\)/)
})

test('editing linked template physical data requires verification invalidation confirmation', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /physicalTemplateChanged/)
  assert.match(source, /linkedSkuCount > 0/)
  assert.match(source, /该模板已关联 \$\{linkedSkuCount\} 个 SKU。修改包装参数后，这些 SKU 的包装验证状态将失效，需要重新确认。是否继续？/)
  assert.match(source, /包装模板变化不会改写历史装箱方案。/)
})
