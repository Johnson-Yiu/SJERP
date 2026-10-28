// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ComboInput from '../src/components/ComboInput.vue'
import { resourceConfigs } from '../src/resourceConfigs.js'

const options = [
  { value: 'US', label: 'United States / US', nameZh: '美国', searchText: 'United States 美国 US USA America' },
  { value: 'DE', label: 'Germany / DE', nameZh: '德国', searchText: 'Germany 德国 DE DEU' },
]

describe('ISS-008 country picker', () => {
  it('filters aliases and supports explicit keyboard selection without custom values', async () => {
    const wrapper = mount(ComboInput, { props: { modelValue: '', options, allowCustom: false, label: '国家/地区' } })
    const input = wrapper.get('input')

    await input.trigger('focus')
    await input.setValue('america')
    expect(wrapper.text()).toContain('United States / US')
    await input.trigger('keydown', { key: 'ArrowDown' })
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(wrapper.emitted('update:modelValue')).toEqual([['US']])
    expect(wrapper.find('.custom-option').exists()).toBe(false)
  })

  it('filters the complete option contract by Chinese name and alpha codes', async () => {
    const wrapper = mount(ComboInput, { props: { modelValue: '', options, allowCustom: false, label: '国家/地区' } })
    const input = wrapper.get('input')

    await input.setValue('德国')
    expect(wrapper.text()).toContain('Germany / DE')
    await input.setValue('DEU')
    expect(wrapper.text()).toContain('Germany / DE')
    await input.setValue('DE')
    expect(wrapper.text()).toContain('Germany / DE')
  })

  it('does not save an unknown typed value when custom entries are disabled', async () => {
    const wrapper = mount(ComboInput, { props: { modelValue: '', options, allowCustom: false } })
    const input = wrapper.get('input')

    await input.setValue('Atlantis')
    await input.trigger('keydown', { key: 'Enter' })
    await input.trigger('blur')

    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('uses the local catalog endpoint for customer editing', () => {
    const countryField = resourceConfigs.customers.fields.find(field => field[0] === 'country')
    expect(countryField.slice(0, 5)).toEqual(['country', '国家/地区', 'combo', false, 'customers/country-catalog'])
  })
})
