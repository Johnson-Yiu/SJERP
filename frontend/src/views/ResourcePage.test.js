import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { resourceConfigs } from '../resourceConfigs.js'

test('resource payload serializes empty optional dates as null', async () => {
  const source = await readFile(new URL('./ResourcePage.vue', import.meta.url), 'utf8')

  assert.match(source, /if \(type === 'date' && value === ''\) value = null/)
})

test('customer next follow-up is visible but is not an editable customer field', async () => {
  const customer = resourceConfigs.customers
  const detail = await readFile(new URL('../components/EntityDetailModal.vue', import.meta.url), 'utf8')

  assert.equal(customer.columns.some(column => column[0] === 'next_follow_up'), true)
  assert.equal(customer.fields.some(field => field[0] === 'next_follow_up'), false)
  assert.match(detail, /currentEntity === 'customers' && item\[0\] === '下次跟进'/)
  assert.match(detail, /由最新跟进记录自动更新/)
})
