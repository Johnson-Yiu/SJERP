import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./ProductPage.vue', import.meta.url)

test('SKU-bearing product prefix changes use preview and explicit apply endpoints', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /editingProduct\.value\?\.sku_count > 0 && prefixChanged\(\)/)
  assert.match(source, /sales-model-prefix-preview/)
  assert.match(source, /sales-model-prefix-apply/)
  assert.match(source, /prefixReview\.value\.baseline/)
  assert.match(source, /确认销售型号前缀变更/)
  assert.match(source, /SKU 编码与历史报价、订单、采购快照不会改变/)
})

test('ordinary product data retains the normal save path', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /await api\.put\(`\/products\/\$\{editingId\.value\}\/`, productPayload\(\)\)/)
  assert.match(source, /await api\.post\('\/products\/', productPayload\(\)\)/)
})
