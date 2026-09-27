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

test('order draft is always a draft and explains that confirmation performs formal actions', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /保存草稿不会接受报价、创建报价迭代版、预留库存或生成应收计划/)
  assert.match(source, /<input value="草稿" readonly/)
  assert.doesNotMatch(source, /option value="shipped"/)
  assert.doesNotMatch(source, /option value="completed"/)
})
