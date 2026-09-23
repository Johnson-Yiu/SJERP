import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { runInNewContext } from 'node:vm'

test('category multiselect supports independent leaves, parent coverage and removal', async () => {
  const source = await readFile(new URL('./CategoryMultiPicker.vue', import.meta.url), 'utf8')
  const props = { modelValue: [], categories: [{ id: 1, name: '灯带', parent: null }, { id: 2, name: 'COB', parent: 1 }, { id: 3, name: '12V', parent: 2 }, { id: 4, name: '电源', parent: null }] }
  const context = { props, computed: fn => ({ get value() { return fn() } }), ref: value => ({ value }), emit: (_, value) => { props.modelValue = Array.from(value) } }
  const script = source.slice(source.indexOf('const path ='), source.indexOf('</script>'))
  runInNewContext(script + ';this.api = { toggle, checked, partial, inherited, remove, browse, columns, labelFor }', context)
  const api = context.api
  api.toggle(props.categories[2], true)
  api.toggle(props.categories[3], true)
  assert.deepEqual(props.modelValue, [3, 4])
  assert.equal(api.partial(1), true)
  api.browse(props.categories[0], 0)
  api.browse(props.categories[1], 1)
  assert.equal(api.columns.value.length, 3)
  assert.equal(api.labelFor(3), '灯带 / COB / 12V')
  api.toggle(props.categories[0], true)
  assert.deepEqual(props.modelValue, [4, 1])
  assert.equal(api.checked(3), true)
  assert.equal(api.inherited(2), true)
  api.toggle(props.categories[2], false)
  assert.deepEqual(props.modelValue, [4, 1])
  api.remove(1)
  assert.deepEqual(props.modelValue, [4])
  assert.equal(api.checked(3), false)
})
