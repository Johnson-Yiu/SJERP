// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'

const mocks = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  listAll: vi.fn(),
}))
vi.mock('../src/api.js', () => ({ ...mocks, listData: response => response.data?.results || response.data || [], downloadQuoteExport: vi.fn() }))

import DocumentPage from '../src/views/DocumentPage.vue'
import ResourcePage from '../src/views/ResourcePage.vue'
import ProductPage from '../src/views/ProductPage.vue'
import PurchaseOrderPage from '../src/views/PurchaseOrderPage.vue'
import PageLoadState from '../src/components/PageLoadState.vue'
import ListEmptyState from '../src/components/ListEmptyState.vue'
import { resourceConfigs } from '../src/resourceConfigs.js'

const customer = { id: 801, name: 'Error State Customer', code: 'C-801', status: 'customer' }
const quote = { id: 801, quote_no: 'QT-801', customer: 801, customer_name: customer.name, status: 'sent', status_display: '已发送', items: [], total_amount: '0' }
let wrapper

async function setup(path) {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/quotes', component: DocumentPage, props: { type: 'quotes' } },
    { path: '/orders', component: DocumentPage, props: { type: 'orders' } },
    { path: '/customers', component: ResourcePage, props: { config: resourceConfigs.customers } },
    { path: '/products', component: ProductPage },
    { path: '/purchase-orders', component: PurchaseOrderPage },
  ] })
  await router.push(path)
  wrapper = mount(defineComponent({ components: { RouterView }, template: '<RouterView />' }), {
    global: {
      plugins: [router],
      stubs: {
        SummaryCards: true, SkuContextBanner: true, QuoteEditorModal: true, QuoteDetailModal: true,
        OrderDraftModal: true, PurchaseDetailModal: true, PurchasePaymentModal: true,
        PurchaseCostAllocationModal: true, SkuPickerPanel: true, TradeUnitPicker: true,
        PaymentTermsEditor: true, ContractAmountAdjustments: true, OperationLogPanel: true,
        EntityDetailModal: true, ComboInput: true, RichTextEditor: true,
        RouterLink: true, Teleport: true,
      },
      directives: { 'money-input': {} },
    },
  })
  await flushPromises()
  return router
}

beforeEach(() => {
  mocks.listAll.mockImplementation(async url => {
    if (url === '/quotes/') return [quote]
    if (url === '/customers/') return [customer]
    if (url === '/products/') return []
    if (url === '/suppliers/' || url === '/orders/' || url === '/skus/' || url === '/purchase-orders/') return []
    return []
  })
  mocks.api.get.mockImplementation(async url => {
    if (url === '/categories/tree/') return { data: [] }
    if (url === '/products/next-code/') return { data: { code: 'P-802' } }
    if (url === '/customers/next-code/') return { data: { code: 'C-802' } }
    return { data: [] }
  })
})
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })

it('shared list states distinguish initial error, refresh progress, true empty, and filtered empty', async () => {
  wrapper = mount(defineComponent({
    components: { PageLoadState, ListEmptyState },
    template: '<div><PageLoadState :loading="false" :has-loaded="false" error="连接失败" /><ListEmptyState entity="客户" /><ListEmptyState entity="客户" :filtered="true" /></div>',
  }))
  expect(wrapper.text()).toContain('数据加载失败')
  expect(wrapper.findAll('.list-empty-state h3').map(node => node.text())).toEqual(['暂无客户', '没有符合当前条件的记录'])
  await wrapper.get('.list-empty-clear').trigger('click')
  expect(wrapper.findAllComponents(ListEmptyState)[1].emitted('clear')).toHaveLength(1)
})

it('shared refresh warning keeps previously loaded content visible', () => {
  wrapper = mount(defineComponent({
    components: { PageLoadState },
    template: '<div><PageLoadState :loading="false" :has-loaded="true" error="网络断开" /><table><tbody><tr><td>QT-801</td></tr></tbody></table></div>',
  }))
  expect(wrapper.text()).toContain('刷新失败，当前显示上一次成功加载的数据')
  expect(wrapper.text()).toContain('QT-801')
})

it('shared state announces refresh progress while leaving rows mounted', () => {
  wrapper = mount(defineComponent({
    components: { PageLoadState },
    template: '<div><PageLoadState :loading="true" :has-loaded="true" /><table><tbody><tr><td>SO-801</td></tr></tbody></table></div>',
  }))
  expect(wrapper.text()).toContain('正在刷新')
  expect(wrapper.text()).toContain('SO-801')
})

it('Document initial list failure shows a persistent load error, and retry replaces it with data', async () => {
  let attempts = 0
  mocks.listAll.mockImplementation(async url => {
    if (url === '/quotes/') { attempts += 1; if (attempts === 1) throw new Error('连接失败'); return [quote] }
    if (url === '/customers/') return [customer]
    return []
  })
  await setup('/quotes')
  expect(wrapper.find('.page-load-state-error').text()).toContain('数据加载失败')
  expect(wrapper.find('.list-empty-state').exists()).toBe(false)
  await wrapper.get('.page-load-state-error button').trigger('click')
  await flushPromises()
  expect(wrapper.find('.page-load-state-error').exists()).toBe(false)
  expect(wrapper.text()).toContain('QT-801')
})

it('Document refresh failure retains the last successful list and shows a persistent warning', async () => {
  let failNext = false
  mocks.listAll.mockImplementation(async url => {
    if (url === '/quotes/') { if (failNext) throw new Error('网络断开'); return [quote] }
    if (url === '/customers/') return [customer]
    return []
  })
  const router = await setup('/quotes')
  expect(wrapper.text()).toContain('QT-801')
  failNext = true
  await router.replace('/quotes?search=QT-801')
  await flushPromises()
  expect(wrapper.find('.page-load-state-warning').text()).toContain('当前显示上一次成功加载的数据')
  expect(wrapper.text()).toContain('QT-801')
})

it('Resource initial failure never becomes an empty customer list, and retry loads customers', async () => {
  let attempts = 0
  mocks.listAll.mockImplementation(async url => {
    if (url === '/customers/') { attempts += 1; if (attempts === 1) throw new Error('服务不可用'); return [customer] }
    return []
  })
  await setup('/customers')
  expect(wrapper.find('.page-load-state-error').exists()).toBe(true)
  expect(wrapper.find('.list-empty-state').exists()).toBe(false)
  expect(wrapper.findComponent({ name: 'SummaryCards' }).exists()).toBe(false)
  await wrapper.get('.page-load-state-error button').trigger('click')
  await flushPromises()
  expect(wrapper.find('.page-load-state-error').exists()).toBe(false)
  expect(wrapper.text()).toContain(customer.name)
})

it('Product category option failure is visible, blocks save, and retry restores editing', async () => {
  let categoryAttempts = 0
  mocks.api.get.mockImplementation(async url => {
    if (url === '/categories/tree/') { categoryAttempts += 1; if (categoryAttempts === 1) throw new Error('分类服务不可用'); return { data: [{ id: 1, name: '灯具', parent: null }] } }
    if (url === '/products/next-code/') return { data: { code: 'P-802' } }
    return { data: [] }
  })
  await setup('/products')
  expect(wrapper.get('.option-load-error').text()).toContain('产品分类资料加载失败')
  await wrapper.get('.option-load-error button').trigger('click')
  await flushPromises()
  expect(wrapper.find('.option-load-error').exists()).toBe(false)
  await wrapper.get('.page-head .btn-primary').trigger('click')
  await flushPromises()
  expect(wrapper.get('.product-modal .modal-foot .btn-primary').element.disabled).toBe(false)
})

it('Purchase reference option failure is visible and successful retry enables the draft editor', async () => {
  let supplierAttempts = 0
  mocks.listAll.mockImplementation(async url => {
    if (url === '/suppliers/') { supplierAttempts += 1; if (supplierAttempts === 1) throw new Error('供应商服务不可用'); return [{ id: 1, name: 'UAT Supplier' }] }
    if (url === '/purchase-orders/') return []
    if (url === '/orders/' || url === '/skus/') return []
    return []
  })
  await setup('/purchase-orders')
  expect(wrapper.get('.option-load-error').text()).toContain('供应商资料加载失败')
  await wrapper.get('.option-load-error button').trigger('click')
  await flushPromises()
  expect(wrapper.find('.option-load-error').exists()).toBe(false)
  await wrapper.get('.page-head .btn-primary').trigger('click')
  await flushPromises()
  expect(wrapper.get('.purchase-create-modal .editor-actions .btn-primary').element.disabled).toBe(false)
})
