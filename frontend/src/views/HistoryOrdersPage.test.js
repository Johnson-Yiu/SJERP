import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./HistoryOrdersPage.vue', import.meta.url)

test('history order entry uses isolated endpoints and keeps the analysis-only label visible', async () => {
  const source = await readFile(componentUrl, 'utf8')
  assert.match(source, /\/orders\/historical\//)
  assert.match(source, /\/purchase-orders\/historical\//)
  assert.match(source, /历史订单 · 仅用于经营分析/)
  assert.match(source, /不生成应收、应付、采购或库存记录/)
})

test('history order entry preserves the supplied historical date and does not expose formal actions', async () => {
  const source = await readFile(componentUrl, 'utf8')
  assert.match(source, /真实订单日期/)
  assert.match(source, /order_date: ''/)
  assert.doesNotMatch(source, /confirm_order|generate-purchase-drafts|payment-plans|ship\//)
})
