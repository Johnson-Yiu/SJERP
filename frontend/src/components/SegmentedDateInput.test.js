import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./SegmentedDateInput.vue', import.meta.url)

test('calendar picker is opened only from its calendar button', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.doesNotMatch(source, /@click\.self="openPicker"/)
  assert.match(source, /aria-label="打开日期选择器" @click="openPicker"/)
})

test('date parts remain compact without individual outlines', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /input:not\(\.native-date-picker\)\{flex:0 0 auto;[^}]*border:0/)
  assert.doesNotMatch(source, /button\{margin-left:auto/)
})
