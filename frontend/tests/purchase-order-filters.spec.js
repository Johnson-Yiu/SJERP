// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

const mocks = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  listAll: vi.fn(),
}))

vi.mock('../src/api.js', () => ({ api: mocks.api, listAll: mocks.listAll, listData: response => response.data.results || response.data }))
vi.mock('../src/dialogs.js', () => ({ confirmDialog: vi.fn(), inputDialog: vi.fn() }))

import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'
import { installModalNavigationGuard } from '../src/utils/modalNavigation.js'

const purchaseRows = [
  { id: 101, purchase_no: 'PO-FILTER-101', supplier: 9, supplier_name: 'Filter Supplier Alpha', order: 31, order_no: 'SO-FILTER-001', order_date: '2031-01-01', status: 'draft', status_display: '草稿', currency: 'USD', total_amount: '10', paid_amount: '0', unpaid_amount: '10', items: [{ sku: 12, sku_code: 'SKU-CTX-12' }] },
  { id: 102, purchase_no: 'PO-FILTER-102', supplier: 9, supplier_name: 'Filter Supplier Alpha', order: 32, order_no: 'SO-FILTER-002', order_date: '2031-01-02', status: 'ordered', status_display: '已下单', currency: 'USD', total_amount: '20', paid_amount: '0', unpaid_amount: '20', items: [{ sku: 13, sku_code: 'SKU-CTX-13' }] },
  { id: 103, purchase_no: 'PO-FILTER-103', supplier: 10, supplier_name: 'Filter Supplier Beta', order: 32, order_no: 'SO-FILTER-002', order_date: '2031-01-03', status: 'partial', status_display: '部分到货', currency: 'USD', total_amount: '30', paid_amount: '0', unpaid_amount: '30', items: [{ sku: 12, sku_code: 'SKU-CTX-12' }] },
  { id: 104, purchase_no: 'PO-FILTER-104', supplier: 10, supplier_name: 'Filter Supplier Beta', order: 33, order_no: 'SO-FILTER-003', order_date: '2031-01-04', status: 'completed', status_display: '已完成', currency: 'USD', total_amount: '40', paid_amount: '0', unpaid_amount: '40', items: [{ sku: 12, sku_code: 'SKU-CTX-12' }] },
  { id: 105, purchase_no: 'PO-FILTER-105', supplier: 9, supplier_name: 'Filter Supplier Alpha', order: 33, order_no: 'SO-FILTER-003', order_date: '2031-01-05', status: 'cancelled', status_display: '已取消', currency: 'USD', total_amount: '50', paid_amount: '0', unpaid_amount: '50', items: [{ sku: 13, sku_code: 'SKU-CTX-13' }] },
]

const optionData = {
  '/suppliers/': [{ id: 9, name: 'Filter Supplier Alpha' }, { id: 10, name: 'Filter Supplier Beta' }],
  '/orders/': [
    { id: 31, order_no: 'SO-FILTER-001', customer_name: 'Filter Customer', status: 'confirmed' },
    { id: 32, order_no: 'SO-FILTER-002', customer_name: 'Filter Customer', status: 'confirmed' },
    { id: 33, order_no: 'SO-FILTER-003', customer_name: 'Filter Customer', status: 'confirmed' },
  ],
  '/skus/': [{ id: 1, sku: 'FILTER-SKU', display_name_cn: '筛选测试 SKU' }],
}

function filterRows(params = {}) {
  let result = [...purchaseRows]
  if (params.sku) result = result.filter(row => row.items.some(item => String(item.sku) === String(params.sku)))
  if (params.search) {
    const term = String(params.search).toLowerCase()
    result = result.filter(row => [row.purchase_no, row.supplier_name, row.order_no].some(value => value.toLowerCase().includes(term)))
  }
  if (params.status) result = result.filter(row => row.status === params.status)
  if (params.pending_receipt === '1') result = result.filter(row => ['ordered', 'partial'].includes(row.status))
  return result
}

let wrapper
let router

async function mountPage(path = '/purchase-orders') {
  router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/purchase-orders', component: PurchaseOrderPage }, { path: '/orders', component: { template: '<div />' } }] })
  installModalNavigationGuard(router)
  await router.push(path)
  await router.isReady()
  wrapper = mount(PurchaseOrderPage, {
    global: {
      plugins: [router],
      stubs: {
        SummaryCards: true,
        TradeUnitPicker: true,
        PurchaseSupplierPicker: true,
        PurchasePaymentModal: true,
        PurchaseCostAllocationModal: true,
        SkuPickerPanel: true,
        ContractAmountAdjustments: true,
      },
      directives: { 'money-input': {} },
    },
  })
  await flushPromises()
  return wrapper
}

function purchaseListCalls() {
  return mocks.listAll.mock.calls.filter(([url]) => url === '/purchase-orders/')
}

async function applySearch(value) {
  await wrapper.find('.purchase-search input').setValue(value)
  await vi.advanceTimersByTimeAsync(300)
  await flushPromises()
}

beforeEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
  mocks.api.get.mockImplementation(async url => ({ data: purchaseRows.find(row => url === `/purchase-orders/${row.id}/`) }))
  mocks.listAll.mockImplementation(async (url, config = {}) => {
    if (url === '/purchase-orders/') return filterRows(config.params)
    return optionData[url] || []
  })
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  router = undefined
  vi.useRealTimers()
})

describe('purchase order list search and filters', () => {
  it('debounces backend search and does not reload reference option datasets', async () => {
    vi.useFakeTimers()
    await mountPage()
    expect(mocks.listAll.mock.calls.filter(([url]) => url !== '/purchase-orders/').map(([url]) => url).sort()).toEqual(['/orders/', '/skus/', '/suppliers/'])
    const initialPurchaseCallCount = purchaseListCalls().length

    await wrapper.find('.purchase-search input').setValue('PO-FILTER-101')
    await vi.advanceTimersByTimeAsync(299)
    await flushPromises()
    expect(purchaseListCalls()).toHaveLength(initialPurchaseCallCount)

    await vi.advanceTimersByTimeAsync(1)
    await flushPromises()
    expect(purchaseListCalls().at(-1)[1].params).toEqual({ search: 'PO-FILTER-101' })
    expect(wrapper.text()).toContain('PO-FILTER-101')
    expect(wrapper.text()).not.toContain('PO-FILTER-102')
    expect(mocks.listAll.mock.calls.filter(([url]) => url !== '/purchase-orders/')).toHaveLength(3)
  })

  it('sends exact status and pending-receipt filters and displays their intersection', async () => {
    await mountPage()
    await wrapper.find('select[aria-label="按状态筛选"]').setValue('ordered')
    await flushPromises()
    expect(purchaseListCalls().at(-1)[1].params).toEqual({ status: 'ordered' })
    expect(wrapper.text()).toContain('PO-FILTER-102')
    expect(wrapper.text()).not.toContain('PO-FILTER-103')

    await wrapper.find('.purchase-pending-filter input').setValue(true)
    await flushPromises()
    expect(purchaseListCalls().at(-1)[1].params).toEqual({ status: 'ordered', pending_receipt: '1' })
    expect(wrapper.text()).toContain('PO-FILTER-102')
    expect(wrapper.text()).not.toContain('PO-FILTER-104')
  })

  it('reset clears search, status, and pending-receipt filters', async () => {
    vi.useFakeTimers()
    await mountPage()
    await applySearch('Filter Supplier Beta')
    await wrapper.find('select[aria-label="按状态筛选"]').setValue('partial')
    await wrapper.find('.purchase-pending-filter input').setValue(true)
    await flushPromises()
    expect(purchaseListCalls().at(-1)[1].params).toEqual({ search: 'Filter Supplier Beta', status: 'partial', pending_receipt: '1' })

    await wrapper.find('.purchase-list-toolbar button').trigger('click')
    await flushPromises()
    expect(purchaseListCalls().at(-1)[1].params).toEqual({})
    expect(wrapper.find('.purchase-search input').element.value).toBe('')
    expect(wrapper.find('select[aria-label="按状态筛选"]').element.value).toBe('')
    expect(wrapper.find('.purchase-pending-filter input').element.checked).toBe(false)
    expect(wrapper.text()).toContain('PO-FILTER-101')
    expect(wrapper.text()).toContain('PO-FILTER-105')
  })

  it('keeps exact detail open when a filter removes that purchase', async () => {
    vi.useFakeTimers()
    await mountPage()
    const draftRow = wrapper.findAll('tbody tr').find(row => row.text().includes('PO-FILTER-101'))
    await draftRow.find('button.text-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.purchase-workbench').exists()).toBe(true)

    await applySearch('PO-FILTER-102')
    expect(wrapper.find('.detail-row').exists()).toBe(false)
    expect(wrapper.text()).toContain('PO-FILTER-102')
    expect(wrapper.find('.purchase-workbench').text()).toContain('PO-FILTER-101')
    expect(mocks.api.get).toHaveBeenCalledWith('/purchase-orders/101/')
  })

  it('sends only the SKU filter for a direct detail URL, shows its context, and closes detail without losing SKU', async () => {
    await mountPage('/purchase-orders?sku=12&detail=101&todo=due')

    expect(purchaseListCalls()[0][1].params).toEqual({ sku: '12' })
    expect(wrapper.text()).toContain('当前 SKU 筛选：SKU-CTX-12')
    expect(wrapper.text()).toContain('PO-FILTER-101')
    expect(wrapper.text()).toContain('PO-FILTER-103')
    expect(wrapper.text()).not.toContain('PO-FILTER-102')
    await flushPromises()
    expect(wrapper.find('.purchase-workbench').exists()).toBe(true)

    await wrapper.get('[aria-label="关闭采购详情"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ sku: '12', todo: 'due' })
  })

  it('clears only SKU context and reloads the destination for Back and Forward SKU changes', async () => {
    await mountPage('/purchase-orders?sku=12&todo=due')
    expect(purchaseListCalls().at(-1)[1].params).toEqual({ sku: '12' })

    await router.push('/purchase-orders?sku=13&todo=due')
    await flushPromises()
    expect(purchaseListCalls().at(-1)[1].params).toEqual({ sku: '13' })
    await router.back()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ sku: '12', todo: 'due' })
    expect(purchaseListCalls().at(-1)[1].params).toEqual({ sku: '12' })
    await router.forward()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ sku: '13', todo: 'due' })
    expect(purchaseListCalls().at(-1)[1].params).toEqual({ sku: '13' })

    await wrapper.find('.sku-context-banner button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ todo: 'due' })
    expect(purchaseListCalls().at(-1)[1].params).toEqual({})
  })
  it('initializes all filters from URL and resets only filter keys while retaining context', async () => {
    await mountPage('/purchase-orders?search=PO-FILTER&status=partial&pending_receipt=1&detail=101&sku=12&order=31&supplier=9&create=1&todo=due')
    expect(wrapper.get('.purchase-search input').element.value).toBe('PO-FILTER')
    expect(wrapper.get('select[aria-label="按状态筛选"]').element.value).toBe('partial')
    expect(wrapper.get('.purchase-pending-filter input').element.checked).toBe(true)
    expect(purchaseListCalls()[0][1].params).toEqual({ search: 'PO-FILTER', status: 'partial', pending_receipt: '1', sku: '12' })
    expect(wrapper.get('.purchase-workbench').text()).toContain('PO-FILTER-101')
    await wrapper.get('.purchase-list-toolbar button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ detail: '101', sku: '12', order: '31', supplier: '9', create: '1', todo: 'due' })
  })

  it('preserves detail and context through debounced search, status and pending changes and Back', async () => {
    vi.useFakeTimers()
    await mountPage('/purchase-orders?detail=101&sku=12&order=31&supplier=9&todo=due')
    await applySearch('PO-FILTER')
    expect(router.currentRoute.value.query.search).toBe('PO-FILTER')
    await wrapper.get('select[aria-label="按状态筛选"]').setValue('partial')
    await flushPromises()
    await wrapper.get('.purchase-pending-filter input').setValue(true)
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ detail: '101', sku: '12', order: '31', supplier: '9', todo: 'due', search: 'PO-FILTER', status: 'partial', pending_receipt: '1' })
    await wrapper.get('.purchase-pending-filter input').setValue(false)
    await flushPromises()
    expect(router.currentRoute.value.query.pending_receipt).toBeUndefined()
    await router.back()
    await flushPromises()
    expect(wrapper.get('.purchase-pending-filter input').element.checked).toBe(true)
    expect(wrapper.get('.purchase-search input').element.value).toBe('PO-FILTER')
    expect(wrapper.get('.purchase-workbench').text()).toContain('PO-FILTER-101')
  })

  it('shows operational counts, business dates and opens a row through its route', async () => {
    await mountPage()
    expect(wrapper.getComponent({ name: 'SummaryCards' }).props('items').map(({label,value}) => [label,value])).toEqual([['执行中',2],['待到货',0],['待付款',3],['已完成',1]])
    expect(wrapper.findAll('thead th').map(cell => cell.text())).toEqual(['采购单号','供应商','来源订单','下单日期','预计到货','状态','采购金额','已付 / 未付','操作'])
    await wrapper.get('.purchase-list-row').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query.detail).toBe('101')
    expect(wrapper.find('.detail-row').exists()).toBe(false)
    expect(wrapper.get('.purchase-workbench').text()).toContain('PO-FILTER-101')
  })

  it('retains route and displays retry when an exact filtered-out detail fails', async () => {
    mocks.api.get.mockRejectedValueOnce(new Error('采购不存在'))
    await mountPage('/purchase-orders?status=completed&detail=101')
    expect(router.currentRoute.value.query).toEqual({ status: 'completed', detail: '101' })
    expect(wrapper.get('[role="alert"]').text()).toContain('采购不存在')
    await wrapper.get('[role="alert"] button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.purchase-workbench').text()).toContain('PO-FILTER-101')
  })

  it('does not discard a pending search when status changes during debounce', async () => {
    vi.useFakeTimers()
    await mountPage()
    await wrapper.get('.purchase-search input').setValue('PO-FILTER')
    await wrapper.get('select[aria-label="按状态筛选"]').setValue('partial')
    await flushPromises()
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ search: 'PO-FILTER', status: 'partial' })
    expect(wrapper.get('.purchase-search input').element.value).toBe('PO-FILTER')
  })

})
