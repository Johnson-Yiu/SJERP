// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const mock = vi.hoisted(() => ({ get: vi.fn(), put: vi.fn() }))
vi.mock('../src/api', () => ({ api: mock }))
import PartyDetailsPanel from '../src/components/PartyDetailsPanel.vue'

beforeEach(() => { mock.get.mockReset(); mock.put.mockReset(); mock.get.mockResolvedValue({ data: { details: null, original_details: null } }); mock.put.mockResolvedValue({ data: {} }) })

describe('party details panel', () => {
  for (const [kind, path] of [['quote', 'quotes'], ['order', 'orders'], ['purchase_order', 'purchase-orders']]) {
    it(`${kind} loads and explicitly saves draft facts`, async () => {
      const wrapper = mount(PartyDetailsPanel, { props: { kind, id: 7, status: 'draft', canEdit: true } })
      await flushPromises()
      expect(mock.get).toHaveBeenCalledWith(`/${path}/7/party-details/`)
      await wrapper.get('input').setValue('Recorded buyer')
      await wrapper.get('button').trigger('click'); await flushPromises()
      expect(mock.put).toHaveBeenCalledWith(`/${path}/7/party-details/`, expect.objectContaining({ details: expect.objectContaining({ buyer: expect.objectContaining({ name: 'Recorded buyer', country: null }) }) }))
    })
  }
  it('shows unknown and explicit empty distinctly without edit permission', async () => {
    const fields = ['name', 'country', 'address', 'tax_id', 'contact', 'phone', 'email', 'billing_address', 'shipping_address', 'recipient']
    const side = Object.fromEntries(fields.map(key => [key, null])); side.name = ''
    mock.get.mockResolvedValue({ data: { details: { schema: 'party-document-details-v1', buyer: side, seller: { ...side } }, original_details: null } })
    const wrapper = mount(PartyDetailsPanel, { props: { kind: 'order', id: 7, status: 'confirmed', canEdit: false } })
    await flushPromises()
    expect(wrapper.text()).toContain('未知'); expect(wrapper.text()).toContain('已留空')
    expect(wrapper.find('input').exists()).toBe(false); expect(mock.put).not.toHaveBeenCalled()
  })
})
