import test from 'node:test'
import assert from 'node:assert/strict'
import { datePreset, resolveBlock, reportBlocks } from './registry.js'

test('date shortcuts handle year and leap-month boundaries in local time', () => {
  assert.deepEqual(datePreset('last-month', new Date(2024, 2, 15)), { date_from: '2024-02-01', date_to: '2024-02-29' })
  assert.deepEqual(datePreset('week', new Date(2026, 8, 13)), { date_from: '2026-09-07', date_to: '2026-09-13' })
  assert.deepEqual(datePreset('quarter', new Date(2026, 8, 11)), { date_from: '2026-07-01', date_to: '2026-09-11' })
  assert.deepEqual(datePreset('30', new Date(2026, 0, 2)), { date_from: '2025-12-04', date_to: '2026-01-02' })
  assert.deepEqual(datePreset('last-year', new Date(2026, 8, 11)), { date_from: '2025-01-01', date_to: '2025-12-31' })
})

test('embedded block overrides do not mutate reusable defaults', () => {
  assert.equal(resolveBlock('sales-country', { view: 'table' }).view, 'table')
  assert.equal(reportBlocks['sales-country'].view, 'bar')
  assert.equal(resolveBlock('inventory-warehouse').metric, 'quantity')
})

test('bank cash facts use an independent report source and date basis', () => {
  assert.deepEqual(resolveBlock('actual-cash-trend').source, 'actual_cash')
  assert.equal(resolveBlock('actual-cash-trend').group_by, 'time')
  assert.equal(resolveBlock('actual-cash-kind').group_by, 'kind')
})
