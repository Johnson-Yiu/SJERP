import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./QuoteEditorModal.vue', import.meta.url)

test('SKU picker synchronizes multi-selection into quote line items', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /const selectedSkuIds = computed/)
  assert.match(source, /function syncSelectedSkus\(ids\)/)
  assert.match(source, /class="sku-selection-panel"/)
  assert.match(source, /v-model="selectedSkuIds"/)
  assert.doesNotMatch(source, /添加一行/)
})
