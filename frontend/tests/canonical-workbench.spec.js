// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import EntityDetailModal from '../src/components/EntityDetailModal.vue'
import { canCreateRelated, orderDetailLocation, purchaseDetailLocation, quoteDetailLocation, relationWorkbenchLocation, workbenchCloseLocation } from '../src/utils/detailNavigation'

const mocks = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock('../src/api', () => ({ api: { get: mocks.get }, listData: response => response.data }))
let wrapper
afterEach(() => wrapper?.unmount())
async function routerAt(path) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<main />' } }] })
  await router.push(path)
  return router
}

it.each([
  ['customers', 'quotes', 'quotes', 'items'],
  ['customers', 'orders', 'orders', 'items'],
  ['suppliers', 'purchases', 'purchase-orders', 'items'],
  ['transactions', 'order', 'orders', 'overview'],
  ['products', 'sales', 'orders', 'items'],
])('drills %s %s directly into a canonical %s workbench', async (source, sectionKey, target, tab) => {
  const path = `/${source}?detail=12&tab=${sectionKey}&search=UAT&status=active`
  const router = await routerAt(path)
  const context = { entity: source, title: 'Source', info: [], metrics: [], sections: [{ key: sectionKey, title: 'Relationship', entity: target, columns: [['name', '记录']], rows: [{ id: 42, name: 'Target' }] }] }
  mocks.get.mockClear()
  mocks.get.mockImplementation(async url => ({ data: url.startsWith('/context/') ? context : url.includes('current-operator') ? { role: '超级管理员' } : [] }))
  wrapper = mount(EntityDetailModal, { props: { entity: source, id: 12 }, global: { plugins: [router], stubs: { ProductWorkspace: { template: '<div><slot /></div>' }, SKUPage: true, OperationLogPanel: true } } })
  await flushPromises()
  await wrapper.find('tbody tr').trigger('click')
  await flushPromises()
  expect(router.currentRoute.value.path).toBe(`/${target}`)
  expect(router.currentRoute.value.query).toMatchObject({ detail: '42', tab, returnTo: path })
  expect(mocks.get.mock.calls.filter(([url]) => url.startsWith('/context/')).map(([url]) => url)).toEqual([`/context/${source}/12/`])
  await router.push(workbenchCloseLocation(router.currentRoute.value))
  expect(router.currentRoute.value.fullPath).toBe(path)
})

it.each(['/quotes?detail=1&tab=orders&search=UAT', '/purchase-orders?detail=3&tab=orders&supplier=8'])('returns from an order to its source workbench %s', async origin => {
  const router = await routerAt(origin)
  await router.push(orderDetailLocation(42, 'overview', router.currentRoute.value.fullPath))
  await router.push(workbenchCloseLocation(router.currentRoute.value))
  expect(router.currentRoute.value.fullPath).toBe(origin)
})

it('closes direct details to their module and rejects external return addresses', async () => {
  for (const origin of [undefined, 'https://evil.example/', '//evil.example/', '/\\evil.example/']) {
    const route = { path: '/orders', query: { detail: '42', tab: 'items', search: 'UAT', ...(origin ? { returnTo: origin } : {}) } }
    expect(workbenchCloseLocation(route)).toEqual({ path: '/orders', query: { search: 'UAT' }, hash: undefined })
  }
  expect(quoteDetailLocation(1)).toEqual({ path: '/quotes', query: { detail: '1' } })
  expect(purchaseDetailLocation(2)).toEqual({ path: '/purchase-orders', query: { detail: '2' } })
  expect(relationWorkbenchLocation('orders', 1, 'skus', 'orders', '/skus?detail=9').query.tab).toBe('items')
})

it.each(['quotes', 'orders', 'purchase-orders'])('%s item relationships do not allow SKU creation', async entity => {
  expect(canCreateRelated(entity, { key: 'items', entity: 'skus' })).toBe(false)
  const router = await routerAt(`/${entity}?detail=12&tab=items`)
  mocks.get.mockImplementation(async url => ({ data: url.startsWith('/context/') ? { entity, title: 'Document', info: [], metrics: [], sections: [{ key: 'items', entity: 'skus', title: '商品明细', columns: [], rows: [] }] } : [] }))
  wrapper = mount(EntityDetailModal, { props: { entity, id: 12 }, global: { plugins: [router], stubs: { OperationLogPanel: true } } })
  await flushPromises()
  expect(wrapper.findAll('.relation-actions button')).toHaveLength(0)
  expect(wrapper.text()).not.toContain('新增SKU')
})
it('allows only explicit customer, supplier and product create roles', () => {
  for (const [source, key, entity] of [['customers', 'contacts', 'contacts'], ['customers', 'followups', 'follow-ups'], ['customers', 'quotes', 'quotes'], ['customers', 'orders', 'orders'], ['suppliers', 'purchases', 'purchase-orders'], ['products', 'skus', 'skus'], ['products', 'parameters', 'product-parameters'], ['products', 'certificates', 'product-certificates']]) expect(canCreateRelated(source, { key, entity })).toBe(true)
  expect(canCreateRelated('orders', { key: 'quote', entity: 'quotes' })).toBe(false)
  expect(canCreateRelated('transactions', { key: 'order', entity: 'orders' })).toBe(false)
  expect(canCreateRelated('inventory-movements', { key: 'order', entity: 'orders' })).toBe(false)
})
