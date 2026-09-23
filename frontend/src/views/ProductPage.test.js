import { readFile } from 'node:fs/promises'
import test from 'node:test'
import assert from 'node:assert/strict'

const componentUrl = new URL('./ProductPage.vue', import.meta.url)

test('product category picker can select a parent category directly', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /直接选择 \$\{category\.name\}/)
  assert.match(source, /@click\.stop="selectCategory\(category\.id\)"/)
  assert.match(source, /<Check :size="14"/)
})
