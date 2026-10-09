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

  assert.match(source, /保存为草稿，确认订单后才预留库存并生成应收计划/)
  assert.match(source, /<input value="草稿" readonly/)
  assert.doesNotMatch(source, /option value="shipped"/)
  assert.doesNotMatch(source, /option value="completed"/)
})

test('order draft does not ask for or submit a backend-generated order number', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /订单编号保存后自动生成/)
  assert.match(source, /delete draftPayload\.order_no/)
  assert.doesNotMatch(source, /v-model="form\.order_no"\s+required/)
})
