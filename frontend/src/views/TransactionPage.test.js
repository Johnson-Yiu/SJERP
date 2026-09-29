import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const pageUrl = new URL('./TransactionPage.vue', import.meta.url)

test('transaction form distinguishes refunds from order expenses', async () => {
  const source = await readFile(pageUrl, 'utf8')

  assert.match(source, /客户退款（原收款退回）/)
  assert.match(source, /供应商退款（原付款退回）/)
  assert.match(source, /用于退回已经收到的订单货款；售后赔偿、运费补贴等请登记为订单费用。/)
  assert.match(source, /用于供应商退回已经支付的采购款。/)
  assert.doesNotMatch(source, /客户退款\/折让/)
  assert.doesNotMatch(source, /供应商退款\/返利/)
})
