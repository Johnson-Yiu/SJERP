import assert from 'node:assert/strict'
import test from 'node:test'

import { addDays, daysBetween } from './orderDate.js'

test('addDays calculates an expected ship date from the order date', () => {
  assert.equal(addDays('2026-08-20', 14), '2026-09-03')
})

test('daysBetween derives the lead time from an expected ship date', () => {
  assert.equal(daysBetween('2026-08-20', '2026-09-03'), 14)
})

test('date helpers leave incomplete dates empty', () => {
  assert.equal(addDays('', 14), '')
  assert.equal(daysBetween('2026-08-20', ''), '')
})
