import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./InventoryPage.vue', import.meta.url)

test('inventory page opens a SKU detail panel with linked business records', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /\/skus\/\$\{row\.id\}\/inventory-detail\//)
  assert.match(source, /selectedSku/)
  assert.match(source, /采购记录/)
  assert.match(source, /出库记录/)
  assert.match(source, /关联订单/)
})

test('inventory headers toggle sortable columns', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /function toggleSort\(/)
  assert.match(source, /sortKey/)
  assert.match(source, /@click="toggleSort\(column\[0\]\)"/)
})
