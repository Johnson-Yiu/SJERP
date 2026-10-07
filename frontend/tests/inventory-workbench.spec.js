// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

const mocks = vi.hoisted(() => ({ api: { get: vi.fn() }, listAll: vi.fn() }))
vi.mock('../src/api.js', () => ({ api: mocks.api, listAll: mocks.listAll }))

import InventoryPage from '../src/views/InventoryPage.vue'

const sku = { id: 12, sku: 'SKU-CTX-12', product_name: 'Context light', unit: 'pcs', display_name_cn: '中文灯具', stock_quantity: 4, actual_quantity: 4, reserved_quantity: 0, available_quantity: 4, in_transit_quantity: 0, to_procure_quantity: 0 }
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
  mocks.listAll.mockResolvedValue([sku, { ...sku, id: 13, sku: 'ZERO', unit: 'm', actual_quantity: 0, available_quantity: 0 }, { ...sku, id: 14, sku: 'GAP', unit: 'm', actual_quantity: 340, to_procure_quantity: 2 }, { ...sku, id: 15, sku: 'ANOMALY', has_anomaly: true }])
  mocks.api.get.mockImplementation(async url => {
    if (url.endsWith('/inventory-detail/')) return { data: inventoryDetail }
    if (url === '/operation-logs/') return { data: [] }
    if (url === '/session/current-operator/') return { data: {} }
    if (url === '/skus/99/') return { data: { ...sku, id: 99 } }
    if (url === '/skus/404/') throw new Error('not found')
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
  wrapper = mount(defineComponent({ template: '<RouterView />' }), {
    global: { plugins: [router], stubs: { OperationLogPanel: true } },
  })
  await flushPromises()
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  router = undefined
})


async function routeTo(query) { await router.push({ path: '/inventory', query }); await flushPromises() }
async function click(text) { await wrapper.findAll('button').find(b => b.text().startsWith(text)).trigger('click'); await flushPromises() }
it('restores URL search and sort and sorts without reloading inventory', async () => {
  await routeTo({ search: 'Context', sort: 'available_quantity', direction: 'desc' })
  expect(wrapper.find('[aria-label="搜索库存"]').element.value).toBe('Context')
  expect(wrapper.find('[aria-label="可用库存：降序"]').exists()).toBe(true)
  await click('可用库存'); expect(router.currentRoute.value.query.direction).toBe('asc')
  await click('已预留'); expect(router.currentRoute.value.query).toMatchObject({ search: 'Context', sort: 'reserved_quantity', direction: 'asc' })
  expect(mocks.listAll).toHaveBeenCalledTimes(1)
})
it('debounces search for 300ms while preserving attention and sort updates', async () => {
  vi.useFakeTimers()
  try {
    await wrapper.find('[aria-label="搜索库存"]').setValue('Context')
    await vi.advanceTimersByTimeAsync(299); expect(router.currentRoute.value.query.search).toBeUndefined()
    await click('仅看待关注'); await click('可用库存')
    await vi.advanceTimersByTimeAsync(1); await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ search: 'Context', attention: '1', sort: 'available_quantity' })
  } finally { vi.useRealTimers() }
})
it('validates sort, direction and tab values with safe defaults', async () => {
  await routeTo({ sort: 'bad', direction: 'bad', detail: '12', tab: 'bad' })
  expect(wrapper.find('[aria-label="SKU：升序"]').exists()).toBe(true)
  expect(wrapper.find('.detail-tabs button.active').text()).toContain('库存流水')
})
it('filters exactly anomaly or procurement gap, excludes zero-only SKU, toggles summary', async () => {
  await routeTo({ attention: '1' })
  expect(wrapper.findAll('.inventory-row').map(x => x.text())).toHaveLength(2)
  expect(wrapper.find('.inventory-table').text()).not.toContain('ZERO')
  expect(wrapper.find('.attention-card').attributes('aria-pressed')).toBe('true')
  await click('待关注'); expect(router.currentRoute.value.query.attention).toBeUndefined()
  expect(wrapper.findAll('.inventory-row')).toHaveLength(4)
  expect(wrapper.findAll('.stock-status').map(x => x.text())).toEqual(['需处理', '待采购', '有库存', '无库存'])
})
it('keeps mixed-unit sums separate and makes base quantity labels explicit', async () => {
  expect(wrapper.find('.inventory-summary').text()).toContain('8 pcs / 340 m')
  expect(wrapper.find('.inventory-helper').text()).toBe('所有库存数量均以 SKU 基础单位显示。')
  expect(wrapper.findAll('thead th').map(x => x.text())).toEqual(['SKU', '中文 SKU 名称', '实际库存', '已预留', '可用库存', '在途采购', '待采购', '状态'])
})
it('opens row with preserved context, closes only detail/tab', async () => {
  const context = { search: 'GAP', attention: '1', sort: 'available_quantity', direction: 'desc', context: 'keep' }
  await routeTo(context); await wrapper.find('.inventory-row').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query).toEqual({ ...context, detail: '14', tab: 'movements' })
  await wrapper.find('[aria-label="关闭库存详情"]').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query).toEqual(context)
})
it('opens filtered-out SKU from full rows and restores exact tab', async () => {
  await routeTo({ search: 'absent', attention: '1', detail: '12', tab: 'purchases' })
  expect(wrapper.findAll('.inventory-row')).toHaveLength(0)
  expect(wrapper.find('.sku-detail h2').text()).toBe(sku.sku)
  expect(wrapper.find('.detail-tabs button.active').text()).toContain('采购记录')
  expect(mocks.api.get).not.toHaveBeenCalledWith('/skus/12/')
})
it('fetches missing full-row SKU identity using detail endpoint', async () => {
  await routeTo({ detail: '99' }); expect(mocks.api.get).toHaveBeenCalledWith('/skus/99/')
  expect(wrapper.find('.sku-detail h2').text()).toBe(sku.sku)
})
it.each(['invalid', '404'])('keeps invalid/deleted detail %s visible with retry and close', async detail => {
  await routeTo({ detail, search: 'Context' })
  expect(wrapper.find('.sku-detail').text()).toContain('库存详情加载失败')
  expect(wrapper.find('.detail-state').text()).toContain('重新加载')
  await wrapper.find('[aria-label="关闭库存详情"]').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.query).toEqual({ search: 'Context' })
})
it('shows exact identity, unchanged six metrics, semantic help and correct tab order', async () => {
  await routeTo({ detail: '12' })
  expect(wrapper.find('.sku-detail header').text()).toContain('中文灯具 · 基础单位：pcs · 有库存')
  expect(wrapper.findAll('.detail-metrics strong').map(x => x.text())).toEqual(['4','0','4','0','0','有库存'])
  expect(wrapper.find('.inventory-semantics').text()).toContain('可用库存：实际库存 - 已预留')
  expect(wrapper.findAll('.detail-tabs button').map(x => x.text().replace(/ \d+$/, ''))).toEqual(['库存流水','关联订单','采购记录','出库记录','SKU 操作日志'])
})
it('maps all five contextual metrics to tabs preserving context and clearing tab search', async () => {
  await routeTo({ detail: '12', tab: 'shipments', search: 'Context', attention: '1' })
  for (const [label, tab] of [['已预留','orders'],['在途采购','purchases'],['实际库存','movements'],['待采购','purchases'],['可用库存','movements']]) {
    await wrapper.find('.detail-filter input').setValue('absent')
    await wrapper.findAll('.metric-link').find(x => x.text().startsWith(label)).trigger('click'); await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ detail: '12', search: 'Context', attention: '1', tab })
    expect(wrapper.find('.detail-filter input').element.value).toBe('')
  }
})
it.each([['purchases','purchase-orders','301'],['orders','orders','501'],['movements','inventory-movements','201']])('exact %s navigation and Browser Back restore context', async (tab,path,id) => {
  await routeTo({ detail: '12', tab, search: 'Context', sort: 'available_quantity', direction: 'desc', attention: '1' })
  const origin = router.currentRoute.value.fullPath
  await wrapper.find('.inventory-detail-link').trigger('click'); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe(`/${path}?sku=12&detail=${id}`)
  router.back(); await new Promise(resolve => setTimeout(resolve, 10)); await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe(origin)
  expect(wrapper.find('.sku-detail h2').text()).toBe(sku.sku)
  expect(wrapper.find('.detail-tabs button.active').text()).toContain({ purchases:'采购记录',orders:'关联订单',movements:'库存流水' }[tab])
})
it('clarifies SKU audit scope and retains existing audit entity', async () => {
  await routeTo({ detail: '12', tab: 'operation_logs' })
  expect(wrapper.find('.sku-log-scope').text()).toContain('这里只显示 SKU 本身的操作记录；库存增减、入库、出库和冲销请查看“库存流水”。')
  expect(wrapper.find('.sku-log-scope').text()).toContain('暂无 SKU 本身的操作记录。')
  expect(mocks.api.get).toHaveBeenCalledWith('/operation-logs/', { params: { entity:'crm.sku',object_id:12,ordering:'-created_at' } })
})
it('retries detail failure retaining exact tab and search', async () => {
  mocks.api.get.mockRejectedValueOnce(new Error('temporary'))
  await routeTo({ detail: '12', tab: 'orders', search: 'Context' })
  expect(wrapper.find('.detail-state.error').exists()).toBe(true)
  await click('重新加载'); expect(wrapper.find('.detail-tabs button.active').text()).toContain('关联订单')
  expect(router.currentRoute.value.query).toEqual({ detail:'12',tab:'orders',search:'Context' })
})

it('restores search, sort, attention, SKU and tab on a fresh component mount', async () => {
  const context = { search:'Context',sort:'available_quantity',direction:'desc',attention:'1',detail:'12',tab:'orders' }
  await routeTo(context); wrapper.unmount()
  wrapper = mount(defineComponent({ template: '<RouterView />' }), { global:{ plugins:[router],stubs:{OperationLogPanel:true} } }); await flushPromises()
  expect(wrapper.find('[aria-label="搜索库存"]').element.value).toBe('Context')
  expect(wrapper.find('[aria-label="可用库存：降序"]').exists()).toBe(true)
  expect(wrapper.find('.sku-detail h2').text()).toBe(sku.sku)
  expect(wrapper.find('.detail-tabs button.active').text()).toContain('关联订单')
  expect(router.currentRoute.value.query).toEqual(context)
})
it('ignores stale responses when switching SKU while detail is loading', async () => {
  let resolveOld
  mocks.api.get.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
  await routeTo({ detail:'12' }); await routeTo({ detail:'14',tab:'purchases' })
  resolveOld({ data:{ ...inventoryDetail, purchases:[{ id:999,purchase_no:'STALE' }] } }); await flushPromises()
  expect(wrapper.find('.sku-detail h2').text()).toBe('GAP')
  expect(wrapper.text()).not.toContain('STALE')
})
