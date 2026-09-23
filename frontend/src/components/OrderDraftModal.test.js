import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./OrderDraftModal.vue', import.meta.url)

test('lead-time input reserves room for ten digits', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /\.lead-time-input>input\{flex:0 0 10ch!important;width:10ch!important/)
})

test('order draft contains one order-level tail-goods policy selector', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /tail_goods_policy/)
  assert.match(source, /此选择对整张订单统一生效/)
})

test('order draft does not offer shipped or completed as manual initial statuses', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /“已发货”由确认出库自动更新/)
  assert.doesNotMatch(source, /option value="shipped"/)
  assert.doesNotMatch(source, /option value="completed"/)
})
