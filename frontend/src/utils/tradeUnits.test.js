import assert from 'node:assert/strict'
import test from 'node:test'
import { fromTradeLine, tradePayload, baseQuantity, restoreTradeLines } from './tradeUnits.js'

test('saved base quantity loads as transaction quantity and sends edited trade quantity', () => {
  const line = fromTradeLine({ sku: 1, quantity: '1000', unit_price: '.8', trade_unit: 2, trade_quantity: '100', trade_unit_price: '8', trade_snapshot: { factor: '10', unit: 'Roll' } })
  assert.equal(line.quantity, '100')
  assert.equal(line.unit_price, '8')
  line.quantity = '30'
  assert.equal(baseQuantity(line), 300)
  const payload = tradePayload(line)
  assert.equal(payload.trade_quantity, '30')
  assert.equal(payload.trade_unit_price, '8')
  assert.equal(payload.trade_snapshot, undefined)
})

test('switching to base unit clears stale transaction values', () => {
  const payload = tradePayload({ trade_unit: null, trade_quantity: '20', trade_unit_price: '5', quantity: '3', unit_price: '2' })
  assert.equal(payload.trade_quantity, undefined)
  assert.equal(payload.quantity, '3')
  assert.equal(baseQuantity(payload), 3)
})

test('receipt cost is interpreted per selected package', () => {
  const payload = tradePayload({ trade_unit: 3, quantity: '2', unit_cost: '60' }, 'unit_cost')
  assert.equal(payload.trade_unit_price, '60')
  assert.equal(payload.trade_quantity, '2')
})

test('SKU selection preserves multiple packaging lines for the same SKU', () => {
  const previous = [{ sku: 1, trade_unit: 10, quantity: 2 }, { sku: 1, trade_unit: 20, quantity: 3 }, { sku: 2, quantity: 1 }]
  const rows = restoreTradeLines([{ sku: 1 }, { sku: 3 }], previous)
  assert.deepEqual(rows, [previous[0], previous[1], { sku: 3 }])
})
