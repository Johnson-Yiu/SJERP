import { expect, it } from 'vitest'
import { resourceConfigs } from '../src/resourceConfigs'

it('keeps supplier notes visible while removing fixed payment rules from regular UI config', () => {
  const supplier = resourceConfigs.suppliers
  expect(supplier.columns).toContainEqual(['payment_terms', '付款条款说明（备注）'])
  expect(supplier.columns).not.toContainEqual(['payment_terms_summary', '系统执行付款规则'])
  expect(supplier.fields).toContainEqual(['payment_terms', '付款条款说明（备注）'])
  expect(supplier.fields).not.toContainEqual(['payment_terms_config', '系统执行付款规则', 'payment_terms'])
  expect(supplier.fields.some(field => field[0] === 'payment_terms_summary')).toBe(false)
})
