import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { runInNewContext } from 'node:vm'

test('supplier filtering and select-all retain selections outside current results', async () => {
  const source = await readFile(new URL('./SupplierBatchBindingDrawer.vue', import.meta.url), 'utf8')
  const context = { computed: fn => ({ get value() { return fn() } }), ref: value => ({ value }), suppliers: { value: [
    { id: 1, name: '灯带供应商', code: 'AA', supply_category_names: ['灯带'], category_match: true },
    { id: 2, name: '电源供应商', code: 'BB', supply_category_names: ['电源'], category_match: false },
  ] }, selected: { value: [] }, search: { value: '' } }
  runInNewContext(source.slice(source.indexOf('const showAll ='), source.indexOf('onMounted(')) + ';this.state = { showAll, visible, selectVisible, allVisibleSelected, selectedSuppliers }', context)
  const state = context.state
  assert.deepEqual(Array.from(state.visible.value, row => row.id), [1])
  state.selectVisible(true)
  state.showAll.value = true
  context.search.value = 'bb'
  state.selectVisible(true)
  assert.deepEqual(Array.from(context.selected.value), [1, 2])
  state.selectVisible(false)
  assert.deepEqual(Array.from(context.selected.value), [1])
  context.search.value = '电源'
  assert.deepEqual(Array.from(state.visible.value, row => row.id), [2])
  state.showAll.value = false
  assert.equal(state.visible.value.length, 0)
  assert.equal(state.selectedSuppliers.value.length, 1)
})
