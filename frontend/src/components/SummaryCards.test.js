import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./SummaryCards.vue', import.meta.url)

test('summary cards provide a reusable, compact metric layout', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /defineProps\(\{ items:/)
  assert.match(source, /v-for="\(item, index\) in items"/)
  assert.match(source, /class="summary-cards"/)
  assert.match(source, /ChartNoAxesCombined/)
  assert.match(source, /container:summary-cards \/ inline-size/)
  assert.match(source, /@container summary-cards \(max-width:760px\)/)
  assert.match(source, /overflow-wrap:anywhere/)
  assert.doesNotMatch(source, /text-overflow:\s*ellipsis/)
  assert.doesNotMatch(source, /white-space:\s*nowrap/)
})
