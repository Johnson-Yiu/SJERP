import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('SKU row Enter does not also open details when an action button has focus', async () => {
  const template = await readFile(new URL('./SKUPage.vue', import.meta.url), 'utf8')
  const row = template.match(/<tr\b[^>]*class="sku-data-row"[^>]*>/)?.[0]
  assert.ok(row)
  assert.match(row, /tabindex="0"/)
  assert.match(row, /@keydown\.enter\.self="openDetail\(row\)"/)
})
