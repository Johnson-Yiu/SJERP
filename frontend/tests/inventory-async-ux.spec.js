// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
const mocks = vi.hoisted(() => ({ listAll: vi.fn(), get: vi.fn(), can: vi.fn() }))
vi.mock('../src/api', () => ({ listAll: mocks.listAll, api: { get: mocks.get } }))
vi.mock('../src/accessControl', () => ({ setAccessOperator: vi.fn(), useAccessControl: () => ({ can: mocks.can }) }))
import InventoryPage from '../src/views/InventoryPage.vue'
const sku = id => ({ id, sku: `SKU-${id}`, unit: 'pcs', actual_quantity: id })
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
let wrapper, router
beforeEach(async () => {
  vi.resetAllMocks(); mocks.can.mockReturnValue(true)
  mocks.listAll.mockResolvedValue([sku(1), sku(2)]); mocks.get.mockResolvedValue({ data: {} })
  router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/inventory', component: InventoryPage },
    { path: '/orders', component: { template: '<div>Orders</div>' } },
  ] })
  await router.push('/inventory'); await router.isReady()
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.useRealTimers() })
async function start() {
  wrapper = mount(defineComponent({ template: '<RouterView />' }), { global: { plugins: [router], stubs: { OperationLogPanel: true } } })
  await flushPromises()
}
async function drawer(id) { await router.push({ path: '/inventory', query: { detail: String(id) } }); await flushPromises() }
async function refresh() { await wrapper.get('.page-head button').trigger('click'); await flushPromises() }
it.each(['success', 'error'])('ignores stale detail %s while refresh delays the next SKU', async outcome => {
  const old = deferred(), list = deferred(), latest = deferred()
  mocks.get.mockImplementation(url => url === '/skus/1/inventory-detail/' ? old.promise : url === '/skus/2/inventory-detail/' ? latest.promise : Promise.resolve({ data: {} }))
  await start(); await drawer(1)
  mocks.listAll.mockReturnValueOnce(list.promise); await refresh(); await drawer(2)
  if (outcome === 'success') old.resolve({ data: { movements: [{ id: 7, movement_no: 'STALE' }] } })
  else old.reject(new Error('OLD ERROR'))
  await flushPromises()
  expect(wrapper.find('.sku-detail h2').text()).toBe('SKU 库存工作台')
  expect(wrapper.text()).not.toContain('OLD ERROR'); expect(wrapper.text()).not.toContain('STALE')
  list.resolve([sku(1), sku(2)]); await flushPromises()
  latest.resolve({ data: { movements: [{ id: 8, movement_no: 'LATEST' }] } }); await flushPromises()
  expect(wrapper.get('.sku-detail h2').text()).toBe('SKU-2'); expect(wrapper.text()).toContain('LATEST')
})
it('keeps a closed drawer closed when pending work completes', async () => {
  const old = deferred(), list = deferred()
  mocks.get.mockImplementation(url => url.endsWith('/inventory-detail/') ? old.promise : Promise.resolve({ data: {} }))
  await start(); await drawer(1)
  mocks.listAll.mockReturnValueOnce(list.promise); await refresh()
  await wrapper.get('[aria-label="关闭库存详情"]').trigger('click'); await flushPromises()
  old.resolve({ data: { movements: [{ movement_no: 'STALE' }] } }); list.resolve([sku(2)]); await flushPromises()
  expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  await drawer(2); expect(wrapper.get('.sku-detail h2').text()).toBe('SKU-2')
})
it('does not return to inventory when queued search runs after leaving', async () => {
  await start(); vi.useFakeTimers()
  await wrapper.get('[aria-label="搜索库存"]').setValue('lamp')
  const leaving = router.push('/orders'); vi.advanceTimersByTime(300)
  await leaving; await flushPromises()
  expect(router.currentRoute.value.path).toBe('/orders')
})
it('shows permission failure rather than empty inventory and supports retry', async () => {
  mocks.listAll.mockRejectedValueOnce({ status: 403, isApiError: true, message: '无权查看库存。', response: { status: 403, data: { detail: '无权查看库存。' } } })
  await start(); expect(wrapper.get('[role="alert"]').text()).toContain('无权查看库存。')
  expect(wrapper.text()).not.toContain('请先在 SKU 管理中添加 SKU。')
  await wrapper.get('[role="alert"] button').trigger('click'); await flushPromises()
  expect(wrapper.findAll('.inventory-row')).toHaveLength(2)
})
it('keeps the standard server-failure message for a normalized HTTP500 response', async () => {
  mocks.listAll.mockRejectedValueOnce({ status: 500, isApiError: true, response: { status: 500, data: { detail: '库存服务失败' } } })
  await start()
  expect(wrapper.get('[role="alert"]').text()).toContain('服务器暂时不可用，请稍后重试。')
  expect(wrapper.get('[role="alert"]').text()).not.toContain('库存服务失败')
  expect(wrapper.findAll('.inventory-row')).toHaveLength(0)
  await wrapper.get('[role="alert"] button').trigger('click'); await flushPromises()
  expect(wrapper.findAll('.inventory-row')).toHaveLength(2)
})
it('retains successful data on refresh error and renders empty success separately', async () => {
  await start(); mocks.listAll.mockRejectedValueOnce(new Error('断网')); await refresh()
  expect(wrapper.get('[role="alert"]').text()).toContain('上一次成功加载的数据')
  expect(wrapper.findAll('.inventory-row')).toHaveLength(2)
  mocks.listAll.mockResolvedValueOnce([]); await refresh()
  expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  expect(wrapper.text()).toContain('请先在 SKU 管理中添加 SKU。')
})
it('hides unauthorized destinations and skips optional SKU logs', async () => {
  mocks.can.mockImplementation(module => module === 'inventory'); await start(); await drawer(1)
  expect(wrapper.findAll('.detail-tabs button').map(button => button.text())).toEqual(['库存流水 0', '出库记录 0'])
  expect(wrapper.find('a[href^="/orders"]').exists()).toBe(false)
  expect(wrapper.find('a[href^="/purchase-orders"]').exists()).toBe(false)
  expect(mocks.get.mock.calls.some(([url]) => url === '/operation-logs/')).toBe(false)
})
