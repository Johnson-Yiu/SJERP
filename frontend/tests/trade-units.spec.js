import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'
import TradeUnitPicker from '../src/components/TradeUnitPicker.vue'

const units = [
  { id: 1, name: '10 米卷', unit: '卷', base_unit: 'm', factor: '10', active: true, allow_fraction: false },
  { id: 2, name: '20 米卷', unit: '卷', base_unit: 'm', factor: '20', active: true, supplier: 7, allow_fraction: false },
  { id: 3, name: '旧 5 米卷', unit: '卷', base_unit: 'm', factor: '5', active: false, allow_fraction: false },
]
const sku = { id: 17, unit: 'm', trade_units: units }

describe('transaction unit picker', () => {
  it('converts the reference price and displays the corresponding base quantity', async () => {
    const line = reactive({ quantity: 2, unit_price: 3 })
    const wrapper = mount(TradeUnitPicker, { props: { sku, line } })
    await wrapper.find('select').setValue('1')
    expect(line.trade_unit).toBe(1)
    expect(line.unit_price).toBe(30)
    expect(wrapper.text()).toContain('2 卷 = 20 m')
    await wrapper.find('select').setValue('')
    expect(line.trade_unit).toBe(null)
    expect(line.unit_price).toBe(3)
  })

  it('preserves the physical quantity when a receipt changes units', async () => {
    const line = reactive({ quantity: 40, unit_cost: 3 })
    const wrapper = mount(TradeUnitPicker, { props: { sku, line, priceField: 'unit_cost', preserveBaseQuantity: true } })
    await wrapper.find('select').setValue('2')
    expect(line.quantity).toBe(2)
    expect(line.unit_cost).toBe(60)
    expect(wrapper.text()).toContain('2 卷 = 40 m')
  })

  it('offers an inactive unit only when inherited from this document', () => {
    const line = reactive({ quantity: 1, unit_price: 3 })
    const fresh = mount(TradeUnitPicker, { props: { sku, line } })
    expect(fresh.find('option[value="3"]').exists()).toBe(false)
    const historical = mount(TradeUnitPicker, { props: { sku, line, historicalUnit: 3 } })
    expect(historical.find('option[value="3"]').exists()).toBe(true)
  })

  it('filters supplier-specific units and explains indivisible quantities', async () => {
    const line = reactive({ quantity: 15, unit_cost: 3 })
    const wrapper = mount(TradeUnitPicker, { props: { sku, line, supplier: 8, preserveBaseQuantity: true, priceField: 'unit_cost' } })
    expect(wrapper.find('option[value="2"]').exists()).toBe(false)
    await wrapper.find('select').setValue('1')
    expect(line.quantity).toBe(1.5)
    expect(wrapper.text()).toContain('仅支持整包装')
  })
})
