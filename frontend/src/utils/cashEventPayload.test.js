import test from 'node:test'
import assert from 'node:assert/strict'
import { optionalSettlementId } from './cashEventPayload.js'

test('no settlement selection is JSON null, never zero or NaN', () => {
  for (const value of ['', ' ', null, undefined, 0, '0', -1, '-1', NaN, 'NaN', Infinity, 'bad', true, {}]) {
    assert.equal(optionalSettlementId(value), null)
    assert.equal(JSON.stringify({ fee_for: optionalSettlementId(value) }), '{"fee_for":null}')
  }
})

test('selected settlement keeps its positive integer identity', () => {
  assert.equal(optionalSettlementId(12), 12)
  assert.equal(optionalSettlementId('12'), 12)
  for (const value of [1.1, Number.MAX_SAFE_INTEGER + 1]) assert.equal(optionalSettlementId(value), null)
})
