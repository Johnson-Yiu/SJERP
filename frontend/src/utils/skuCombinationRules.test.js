import test from 'node:test'
import assert from 'node:assert/strict'
import { matchesCombinationRules } from './skuCombinationRules.js'
const definitions = [{ key: '1:voltage', name: '电压', unit: 'V' }, { key: '1:length', name: '长度', unit: '米' }]
const rule = (when, value, op = 'eq') => ({ when: '1:voltage', when_values: when, target: '1:length', op, values: value })
test('preview filters cartesian combinations by all rules and normalizes units', () => {
  const rules = [rule(['12V'], ['5米']), rule(['24V'], ['10米'])]
  const combinations = ['12', '24'].flatMap(v => ['5', '10'].map(l => ({ voltage: v, length: l })))
  assert.deepEqual(combinations.filter(v => matchesCombinationRules(v, rules, definitions)), [{ voltage: '12', length: '5' }, { voltage: '24', length: '10' }])
})
test('multi-trigger, allowed values, prohibition and empty rules', () => {
  const values = { voltage: '24v', length: '5米' }
  assert.equal(matchesCombinationRules(values, [rule(['12V', '24V'], ['5米', '10米'], 'in')], definitions), true)
  assert.equal(matchesCombinationRules(values, [rule(['24V'], ['5米'], 'neq')], definitions), false)
  assert.equal(matchesCombinationRules(values, [], definitions), true)
  assert.equal(matchesCombinationRules(values, [{ ...rule([], ['10米']), when: '' }], definitions), false)
})
