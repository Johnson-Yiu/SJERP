import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { resolveDetailForPreview } from '../utils/skuDetails.js'

const componentUrl = new URL('./SKUPage.vue', import.meta.url)

test('SKU editor exposes supplier source maintenance through the API', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /Supplier Sources/)
  assert.match(source, /listAll\('\/supplier-skus\//)
  assert.match(source, /api\.post\('\/supplier-skus\//)
  assert.match(source, /api\.patch\(`\/supplier-skus\//)
  assert.match(source, /supplier_sku_code/)
  assert.match(source, /is_preferred/)
  assert.match(source, /toggleSupplierSource/)
  assert.match(source, /inheritedProduct/)
})

test('SKU editor canonicalizes abbreviation keys and mirrors backend value formatting', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /normalizeAbbreviationKey/)
  assert.match(source, /toLocaleLowerCase\(\)\.replace\(\/\\s\+\/g, ' '\)/)
  assert.match(source, /const formatParameterValue = \(attribute, value\)/)
  assert.match(source, /endsWith\(unit\.toLocaleLowerCase\(\)\)/)
  assert.match(source, /identity_change_confirmed: identityChanged/)
  assert.match(source, /deactivateRow/)
})

test('SKU creation relies on generated Sales Model and reviews identity changes before saving', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /v-if="editingId" class="field sales-model-field"/)
  assert.match(source, /sales_model: null/)
  assert.match(source, /identityReviewOpen/)
  assert.match(source, /diff-removed/)
  assert.match(source, /确认后系统会再次检查中文名称、Sales Model 和参数组合是否与其他 SKU 重复/)
})

test('editing one SKU keeps its packaging detail when the computed preview key changes', () => {
  const detail = { preview_key: '', packaging_template: 17, packaging_query: 'Template A', unit_weight: 0.5, carton_quantity: 10 }
  const resolved = resolveDetailForPreview([detail], { key: '12W|3000K' }, 1, () => ({ packaging_template: '' }))

  assert.equal(resolved, detail)
  assert.equal(resolved.preview_key, '12W|3000K')
  assert.equal(resolved.packaging_template, 17)
  assert.equal(resolved.unit_weight, 0.5)
  assert.equal(resolved.carton_quantity, 10)
})


test('saved parameter suggestions include inherited categories and legacy keys independent of search rows', async () => {
  const { runInNewContext } = await import('node:vm')
  const source = await readFile(componentUrl, 'utf8')
  const code = source.slice(source.indexOf('const optionsFor ='), source.indexOf('const splitValues ='))
  const context = {
    form: { product: 2 }, parameters: { value: [] },
    productById: { value: new Map([[2, { id: 2, category: 27 }], [3, { id: 3, category: 26 }], [4, { id: 4, category: 21 }]]) },
    categoryMap: { value: new Map([[27, { parent: 25 }], [26, { parent: 25 }], [25, { parent: 10 }], [10, { parent: 2 }], [21, { parent: 8 }]]) },
    rows: { value: [] },
    historyRows: { value: [
      { product: 2, parameter_values: { '2:输入电压': '12V', '2:色温': '3000K' } },
      { product: 3, parameter_values: { '2:输入电压': '24V' } },
      { product: 4, parameter_values: { '2:输入电压': '220V' } },
    ] },
    splitValues: value => String(value || '').split('\n').filter(Boolean),
  }
  runInNewContext(code + ';this.optionsFor = optionsFor', context)
  assert.deepEqual(Array.from(context.optionsFor({ id: 2 }, { key: '输入电压', name: '输入电压', default_value: '48V' }, false), item => item.value), ['12V', '24V'])
  assert.deepEqual(Array.from(context.optionsFor({ id: 2 }, { key: '色温/发光颜色', name: '色温/发光颜色' }, false), item => item.value), ['3000K'])
})
