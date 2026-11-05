import test from 'node:test'
import assert from 'node:assert/strict'
import { safeReturn } from './safeReturn.js'

test('return path remains on the ERP origin', () => {
  const origin = 'https://erp.example.invalid'
  for (const value of ['https://elsewhere.invalid', '//elsewhere.invalid', '/\\elsewhere.invalid', '/\nelsewhere', null]) {
    assert.equal(safeReturn(value, origin), '/')
  }
  assert.equal(safeReturn('/customers?detail=1', origin), '/customers?detail=1')
})
