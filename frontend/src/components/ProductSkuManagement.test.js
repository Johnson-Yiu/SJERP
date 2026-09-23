import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { runInNewContext } from 'node:vm'

test('SKU candidate filters combine values with OR and attributes with AND, including legacy keys', async () => {
  const source = await readFile(new URL('./ProductSkuManagement.vue', import.meta.url), 'utf8')
  const start = source.indexOf('const candidatePoolRows =')
  const end = source.indexOf('const candidateSourceLabels', start)
  const context = { computed: fn => ({ get value() { return fn() } }), skuRows: { value: [
    { id: 1, active: true, sku: 'A', parameter_values: { '2:voltage': '12V', '2:色温': '3000K' } },
    { id: 2, active: true, sku: 'B', parameter_values: { '2:voltage': '24V', '2:色温': '3000K' } },
    { id: 3, active: true, sku: 'C', parameter_values: { '2:voltage': '24V', '2:色温': '4000K' } },
  ] }, candidatePool: { value: { rows: [] } }, showInactive: { value: false }, poolSearch: { value: '' }, poolSource: { value: '' }, state: { value: { definitions: [{ category_id: 2, key: 'voltage', name: '电压' }, { category_id: 2, key: '色温/发光颜色', name: '色温/发光颜色' }] } }, parameterFilters: { value: { '2:voltage': ['12V', '24V'], '2:色温/发光颜色': ['3000K'] } } }
  const helpers = source.slice(source.indexOf('const keyFor ='), source.indexOf('const visibleSkus ='))
  runInNewContext(helpers + source.slice(start, end) + ';this.filtered = candidatePoolRows', context)
  assert.deepEqual(Array.from(context.filtered.value, row => row.sku_id), [1, 2])
  context.poolSearch.value = '24v'
  assert.deepEqual(Array.from(context.filtered.value, row => row.sku_id), [2])
  context.parameterFilters.value = {}
  assert.deepEqual(Array.from(context.filtered.value, row => row.sku_id), [2, 3])
})
