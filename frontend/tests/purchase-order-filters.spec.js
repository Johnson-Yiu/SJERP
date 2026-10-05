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
  { id: 101, purchase_no: 'PO-FILTER-101', supplier: 9, supplier_name: 'Filter Supplier Alpha', order: 31, order_no: 'SO-FILTER-001', order_date: '2031-01-01', status: 'draft', status_display: '草稿', currency: 'USD', total_amount: '10', paid_amount: '0', unpaid_amount: '10', items: [] },
  { id: 102, purchase_no: 'PO-FILTER-102', supplier: 9, supplier_name: 'Filter Supplier Alpha', order: 32, order_no: 'SO-FILTER-002', order_date: '2031-01-02', status: 'ordered', status_display: '已下单', currency: 'USD', total_amount: '20', paid_amount: '0', unpaid_amount: '20', items: [] },
  { id: 103, purchase_no: 'PO-FILTER-103', supplier: 10, supplier_name: 'Filter Supplier Beta', order: 32, order_no: 'SO-FILTER-002', order_date: '2031-01-03', status: 'partial', status_display: '部分到货', currency: 'USD', total_amount: '30', paid_amount: '0', unpaid_amount: '30', items: [] },
  { id: 104, purchase_no: 'PO-FILTER-104', supplier: 10, supplier_name: 'Filter Supplier Beta', order: 33, order_no: 'SO-FILTER-003', order_date: '2031-01-04', status: 'completed', status_display: '已完成', currency: 'USD', total_amount: '40', paid_amount: '0', unpaid_amount: '40', items: [] },
  { id: 105, purchase_no: 'PO-FILTER-105', supplier: 9, supplier_name: 'Filter Supplier Alpha', order: 33, order_no: 'SO-FILTER-003', order_date: '2031-01-05', status: 'cancelled', status_display: '已取消', currency: 'USD', total_amount: '50', paid_amount: '0', unpaid_amount: '50', items: [] },
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

async function mountPage() {
  router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/purchase-orders', component: PurchaseOrderPage }] })
  installModalNavigationGuard(router)
  await router.push('/purchase-orders')
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

  it('closes an expanded row when a filter removes that purchase', async () => {
    vi.useFakeTimers()
    await mountPage()
    const draftRow = wrapper.findAll('tbody tr').find(row => row.text().includes('PO-FILTER-101'))
    await draftRow.find('button.text-btn').trigger('click')
    expect(wrapper.find('.detail-row').exists()).toBe(true)

    await applySearch('PO-FILTER-102')
    expect(wrapper.find('.detail-row').exists()).toBe(false)
    expect(wrapper.text()).toContain('PO-FILTER-102')
    expect(wrapper.text()).not.toContain('PO-FILTER-101')
  })
})
