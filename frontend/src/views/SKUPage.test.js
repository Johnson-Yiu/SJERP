import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { resolveDetailForPreview } from '../utils/skuDetails.js'

const componentUrl = new URL('./SKUPage.vue', import.meta.url)

test('SKU editor exposes supplier source maintenance through the API', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /<h4>供应来源<\/h4>/)
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

test('SKU creation relies on generated Sales Model and editing preserves the saved model', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /v-if="editingId" class="field sales-model-field"/)
  assert.match(source, /sales_model: null/)
  assert.match(source, /identityReviewOpen/)
  assert.match(source, /diff-removed/)
  assert.match(source, /确认后系统会再次检查中文名称、Sales Model 和参数组合是否与其他 SKU 重复/)
  assert.match(source, /const salesModel = form\.sales_model \|\| null/)
  assert.match(source, /当前保存型号：\{\{ form\.sales_model \|\| '未设置' \}\}/)
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

async function saveContext(editing = false, imageFails = false, salesModel = '', parameterChanged = false) {
  const { runInNewContext } = await import('node:vm')
  const source = await readFile(componentUrl, 'utf8')
  const calls = [], notices = []
  const detail = { packaging_template: 12, carton_quantity: 50, unit_weight: 0.15 }
  const preview = { specification: '12W', parameterValuesForSku: { power: '12W' }, description_cn: 'Light' }
  const ctx = {
    api: { put: async (...args) => { calls.push(['put', ...args]) }, post: async (...args) => { calls.push(['post', ...args]); return { data: [{ id: 7 }] } } },
    guard: { markClean: () => calls.push(['clean']) }, nextTick: async () => {},
    saveError: { value: '' }, saving: { value: false }, editingId: { value: editing ? 7 : null },
    form: { product: 1, unit: 'pcs', currency: 'USD', active: true, sales_model: salesModel }, salesModelAbbreviations: {},
    allPreviews: { value: [preview] }, chosenPreviews: { value: [preview] }, detailFor: () => detail,
    cleanDetail: () => ({ carton_quantity: 50 }), ordinaryValues: () => ({}), translateLightingTerms: v => v,
    selectedImage: { value: imageFails ? {} : null }, imageClearRequested: { value: false }, pendingImageSkuIds: { value: [] }, pendingImageFailurePrefix: { value: "" },
    skuOptionsReady: { value: true },
    uploadImage: async () => { if (imageFails) throw new Error('network failed') },
    load: async () => {}, closeModal: () => calls.push(['close']), emit: () => {},
    notify: msg => notices.push(msg), reportSaveError: (error, prefix) => { ctx.saveError.value = prefix + error.message; notices.push(ctx.saveError.value) },
  }
  const helper = source.slice(source.indexOf('function packagingInput('), source.indexOf('async function openVersions'))
  const persist = source.slice(source.indexOf('async function persistSave('), source.indexOf('async function confirmIdentitySave'))
  runInNewContext(helper + persist + ';this.persistSave = persistSave', ctx)
  await ctx.persistSave({ editingRow: { specification: '12W', parameter_values: {} }, parameterChanged, productChanged: false, identityChanged: false })
  return { ctx, calls, notices }
}

test('create and edit include packaging in their single SKU database request', async () => {
  for (const editing of [false, true]) {
    const { calls } = await saveContext(editing)
    const writes = calls.filter(([method]) => method === 'post' || method === 'put')
    assert.equal(writes.length, 1)
    const input = editing ? writes[0][2] : writes[0][2].items[0]
    assert.equal(input.packaging_profile_input.packaging_template, 12)
    assert.equal(input.packaging_profile_input.qty_per_carton_override, 50)
    assert.equal(input.packaging_profile_input.unit_net_weight, 0.15)
  }
})

test('parameter edits submit the explicitly saved Sales Model instead of the generated preview', async () => {
  const { calls } = await saveContext(true, false, 'CUSTOM-REVISED', true)
  const write = calls.find(([method]) => method === 'put')
  assert.equal(write[2].sales_model, 'CUSTOM-REVISED')
})

test('image failure retains saved SKU IDs for independent retry and reports database success', async () => {
  for (const editing of [false, true]) {
    const { ctx, calls, notices } = await saveContext(editing, true)
    assert.equal(ctx.pendingImageSkuIds.value[0], 7)
    assert.ok(notices.some(msg => msg.includes(editing ? 'SKU 已更新，但图片上传失败' : 'SKU 已创建，但图片上传失败')))
    assert.equal(calls.filter(([method]) => method === 'post' || method === 'put').length, 1)
    assert.ok(!calls.some(([method]) => method === 'close'))
    assert.ok(calls.some(([method]) => method === 'clean'))
  }
})

test('nested packaging validation messages remain readable', async () => {
  const { apiErrorMessage } = await import('../utils/apiErrors.js')
  assert.equal(apiErrorMessage({ response: { status: 400, data: { packaging_profile_input: { qty_per_carton_override: ['每箱数量必须大于 0。'] } } }, status: 400 }), '包装设置 · 每箱数量：每箱数量必须大于 0。')
})
