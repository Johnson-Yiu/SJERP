// @vitest-environment jsdom
import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PaymentTermsEditor from '../src/components/PaymentTermsEditor.vue'
import { defaultPaymentTerms, paymentTermsError, percentToRatio, copyPaymentTerms } from '../src/utils/paymentTerms'

it('validates exact decimal totals, empty stages and invalid fields', () => {
  expect(paymentTermsError(defaultPaymentTerms())).toBe('')
  expect(percentToRatio('20.05')).toBe('0.2005')
  expect(paymentTermsError([])).toContain('1 至 5')
  for (const [key, value] of [['ratio', '0.29'], ['ratio', '0'], ['label', ''], ['offset_days', -1], ['offset_days', 0.5], ['due_basis', 'bad']]) {
    const rows = defaultPaymentTerms(); rows[0][key] = value
    expect(paymentTermsError(rows)).not.toBe('')
  }
  const exact = [{ label: 'A', ratio: '0.1234567890123456789', due_basis: 'no_date', offset_days: 0 }, { label: 'B', ratio: '0.8765432109876543211', due_basis: 'no_date', offset_days: 0 }]
  expect(paymentTermsError(exact)).toBe('')
  exact[1].ratio = '0.8765432109876543212'
  expect(paymentTermsError(exact)).toContain('100%')
})
it('renders natural labels, stages and validation while emitting isolated overrides', async () => {
  const original = defaultPaymentTerms()
  const wrapper = mount(PaymentTermsEditor, { props: { modelValue: copyPaymentTerms(original) } })
  await wrapper.get('[aria-label="比例 % 1"]').setValue('20')
  const changed = wrapper.emitted('update:modelValue').at(-1)[0]
  expect(changed[0].ratio).toBe('0.20')
  expect(original[0].ratio).toBe('0.30')
  await wrapper.setProps({ modelValue: changed })
  expect(wrapper.get('[role="alert"]').text()).toContain('100%')
  expect(wrapper.text()).toContain('合计：90%')
  wrapper.unmount()
})
