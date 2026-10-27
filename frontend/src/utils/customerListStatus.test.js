import assert from 'node:assert/strict'
import test from 'node:test'
import { customerListStatus } from './customerListStatus.js'

test('customer lifecycle keys use the canonical Chinese labels', () => {
  assert.deepEqual(
    ['lead', 'contact', 'opportunity', 'customer', 'company'].map(status => customerListStatus(status)),
    ['线索', '已联系', '商机', '正式客户', '返单客户'],
  )
})

test('unknown customer lifecycle keys keep their safe fallback', () => {
  assert.equal(customerListStatus('legacy', '原始状态'), '原始状态')
})
