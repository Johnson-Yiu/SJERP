// @vitest-environment jsdom
import { expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import HistoryOrdersPage from '../src/views/HistoryOrdersPage.vue'

const { get } = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock('../src/composables/useWorkspaceApi', () => ({
  useWorkspaceApi: () => ({ api: { get }, listAll: async () => [] }),
}))
vi.mock('../src/accessControl', () => ({ useAccessControl: () => ({ can: () => true }) }))

it('ignores initial and switched analysis responses that arrive after the accepted request', async () => {
  const requests = []
  get.mockImplementation((url, { params }) => new Promise((resolve, reject) => requests.push({ params, resolve, reject })))
  const wrapper = mount(HistoryOrdersPage, { global: { stubs: { RouterLink: true } } })
  const grouping = wrapper.get('.analysis-filter select')
  const card = wrapper.get('.analysis-card')
  const result = label => ({ data: { sales: { by_sku: [{ label, quantity: 1, amount: 2 }] } } })
  await grouping.setValue('linked')
  await grouping.setValue('original')
  expect(requests.map(item => item.params.grouping)).toEqual(['original', 'linked', 'original'])
  requests[2].resolve(result('最新原始商品'))
  await flushPromises()
  expect(card.get('h5').text()).toBe('历史原文')
  expect(card.text()).toContain('最新原始商品')

  requests[1].resolve(result('旧正式 SKU'))
  requests[0].reject(new Error('迟到的初次请求错误'))
  await flushPromises()
  expect(card.get('h5').text()).toBe('历史原文')
  expect(card.text()).toContain('最新原始商品')
  expect(card.text()).not.toMatch(/旧正式 SKU|迟到的初次请求错误/)
  expect(grouping.element.value).toBe('original')

  await grouping.setValue('linked')
  requests[3].reject(new Error('本次分析失败'))
  await flushPromises()
  expect(card.get('[role=alert]').text()).toContain('本次分析失败')
  await wrapper.get('.analysis-filter button').trigger('click')
  requests[4].resolve(result('重试成功的正式 SKU'))
  await flushPromises()
  expect(card.get('h5').text()).toBe('按关联 SKU 归集')
  expect(card.text()).toContain('重试成功的正式 SKU')
  wrapper.unmount()
})
