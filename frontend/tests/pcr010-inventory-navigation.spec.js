// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn() }, listAll: vi.fn() }))
vi.mock('../src/api.js', () => ({ api: mocks.api, listAll: mocks.listAll }))

import InventoryPage from '../src/views/InventoryPage.vue'

const sku = { id: 12, sku: 'SKU-CTX-12', product_name: 'Context light', unit: 'pcs', stock_quantity: 4, actual_quantity: 4, reserved_quantity: 0, available_quantity: 4, in_transit_quantity: 0, to_procure_quantity: 0 }
const inventoryDetail = {
  sku,
  movements: [{ id: 201, movement_no: 'IM-CTX-201', movement_date: '2026-10-05', type_display: '盘盈入库', signed_quantity: '2', warehouse: '默认仓', reference: '', notes: '', trade_snapshot: {} }],
  purchases: [{ id: 301, purchase_no: 'PO-CTX-301', supplier_name: 'Context Supplier', quantity: '2', received_quantity: '0', status_display: '已下单' }],
  shipments: [{ id: 401, shipment_no: 'SH-CTX-401', order: 501, order_no: 'SO-CTX-501', shipment_date: '2026-10-05', quantity: '1' }],
  orders: [{ id: 501, order_no: 'SO-CTX-501', customer_name: 'Context Buyer', quantity: '3', shipped_quantity: '1', status_display: '已发货' }],
}

const Destination = defineComponent({ template: '<div />' })
let wrapper
let router

async function openSkuDrawer() {
  await router.push('/inventory')
  await flushPromises()
  await wrapper.find('tr.inventory-row').trigger('click')
  await flushPromises()
}

async function chooseTab(title) {
  const button = wrapper.findAll('.detail-tabs button').find(row => row.text().includes(title))
  await button.trigger('click')
  await flushPromises()
}

beforeEach(async () => {
  vi.clearAllMocks()
  mocks.listAll.mockResolvedValue([sku])
  mocks.api.get.mockImplementation(async url => {
    if (url === '/skus/12/inventory-detail/') return { data: inventoryDetail }
    if (url === '/operation-logs/') return { data: [] }
    if (url === '/session/current-operator/') return { data: {} }
    return { data: {} }
  })
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/inventory', component: InventoryPage },
      { path: '/orders', component: Destination },
      { path: '/purchase-orders', component: Destination },
      { path: '/inventory-movements', component: Destination },
    ],
  })
  await router.push('/inventory')
  await router.isReady()
  wrapper = mount(InventoryPage, {
    global: { plugins: [router], stubs: { OperationLogPanel: true } },
  })
  await flushPromises()
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  router = undefined
})

describe('PCR-010 Inventory SKU navigation', () => {
  it('offers the three SKU-scoped destinations from the selected SKU drawer', async () => {
    await openSkuDrawer()
    const links = wrapper.findAll('.sku-context-actions a')
    expect(links.map(link => [link.text(), link.attributes('href')])).toEqual([
      ['采购单', '/purchase-orders?sku=12'],
      ['销售订单', '/orders?sku=12'],
      ['库存流水', '/inventory-movements?sku=12'],
    ])
  })

  it('links movement, purchase, related order, and shipment order identifiers to numeric detail routes', async () => {
    await openSkuDrawer()
    let recordLink = wrapper.find('.detail-table-wrap a.inventory-detail-link')
    expect(recordLink.text()).toBe('IM-CTX-201')
    expect(recordLink.attributes('href')).toBe('/inventory-movements?sku=12&detail=201')
    await recordLink.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/inventory-movements?sku=12&detail=201')

    await openSkuDrawer()
    await chooseTab('采购记录')
    recordLink = wrapper.find('.detail-table-wrap a.inventory-detail-link')
    expect(recordLink.text()).toBe('PO-CTX-301')
    expect(recordLink.attributes('href')).toBe('/purchase-orders?sku=12&detail=301')
    await recordLink.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/purchase-orders?sku=12&detail=301')

    await openSkuDrawer()
    await chooseTab('关联订单')
    recordLink = wrapper.find('.detail-table-wrap a.inventory-detail-link')
    expect(recordLink.attributes('href')).toBe('/orders?sku=12&detail=501')

    await chooseTab('出库记录')
    recordLink = wrapper.find('.detail-table-wrap a.inventory-detail-link')
    expect(recordLink.text()).toBe('SO-CTX-501')
    expect(recordLink.attributes('href')).toBe('/orders?sku=12&detail=501')
    await recordLink.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/orders?sku=12&detail=501')
  })
})
