import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { resourceConfigs } from '../resourceConfigs.js'

test('resource payload serializes empty optional dates as null', async () => {
  const source = await readFile(new URL('./ResourcePage.vue', import.meta.url), 'utf8')

  assert.match(source, /if \(type === 'date' && value === ''\) value = null/)
})

test('customer projections are visible but not editable customer fields', async () => {
  const customer = resourceConfigs.customers
  const page = await readFile(new URL('./ResourcePage.vue', import.meta.url), 'utf8')
  const detail = await readFile(new URL('../components/EntityDetailModal.vue', import.meta.url), 'utf8')

  assert.equal(customer.columns.some(column => column[0] === 'next_follow_up'), true)
  assert.equal(customer.fields.some(field => field[0] === 'next_follow_up'), false)
  assert.equal(customer.columns.some(column => column[0] === 'status'), true)
  assert.equal(customer.fields.some(field => field[0] === 'status'), false)
  assert.match(customer.description, /客户阶段由跟进、报价和正式订单自动更新/)
  assert.match(page, /contact: '已建立联系'/)
  assert.match(page, /opportunity: '已进入报价阶段'/)
  assert.match(page, /customer: '已有1张正式订单'/)
  assert.match(page, /company: '已有2张及以上正式订单'/)
  assert.match(detail, /currentEntity === 'customers' && item\[0\] === '下次跟进'/)
  assert.match(detail, /由最新跟进记录自动更新/)
})
