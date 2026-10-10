// @vitest-environment jsdom
import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SkuPickerPanel from '../src/components/SkuPickerPanel.vue'
it.each(['USD', null])('SKU default prices display their own currency or a safe placeholder (%s)', currency => {
  const wrapper = mount(SkuPickerPanel, { props: { skus: [{ id: 1, sku: 'UAT-SKU', currency, default_price: '9.90', unit: 'pcs' }], activeId: 1 } })
  const label = currency || '币种未设置'
  expect(wrapper.get('.sku-picker-options em').text()).toBe(`${label} 9.90`)
  expect(wrapper.get('.sku-picker-preview').text()).toContain(`pcs / ${label} 9.90`)
  wrapper.unmount()
})
