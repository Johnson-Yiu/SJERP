// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

const mocks = vi.hoisted(() => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

vi.mock('../src/api.js', () => ({
  api: mocks.api,
  listData: response => response?.data?.results || response?.data || [],
}))

vi.mock('../src/dialogs', () => ({ confirmDialog: vi.fn() }))

import EntityDetailModal from '../src/components/EntityDetailModal.vue'

const RelatedCreateHarness = defineComponent({
  name: 'RelatedCreateModal',
  props: { entity: String, query: { type: Object, default: () => ({}) } },
  emits: ['close', 'saved'],
  setup(props, { emit }) {
    return () => h('div', { 'data-test': 'related-create' }, [
      h('span', { 'data-test': 'quote-seed' }, `${props.entity}:${props.query.customer || ''}`),
      h('button', { 'data-test': 'related-close', onClick: () => emit('close') }, '取消报价'),
      h('button', {
        'data-test': 'related-save',
        onClick: () => emit('saved', { id: 901, quote_no: 'QT-UAT-0901', status: 'draft' }),
      }, '模拟保存'),
    ])
  },
})

const OperationLogStub = defineComponent({ name: 'OperationLogPanel', template: '<div />' })
const EmptyPageStub = defineComponent({ template: '<div />' })

function customerContext(quotes = []) {
  return {
    entity: 'customers',
    title: 'Orion Lighting GmbH',
    subtitle: 'Customer · CUST-ORION',
    badge: '客户',
    info: [],
    metrics: [],
    sections: [
      { key: 'quotes', title: '报价记录', entity: 'quotes', rows: quotes, columns: [['quote_no', '报价单号']] },
      { key: 'followups', title: '跟进记录', entity: 'follow-ups', rows: [], columns: [] },
    ],
  }
}

function followUpContext() {
  return {
    entity: 'follow-ups',
    title: 'UAT quote follow-up',
    subtitle: '跟进记录 · 2026-10-06 10:00',
    badge: '邮件',
    info: [['客户回复 / 客户疑问', '请准备报价。'], ['下次跟进', '2026-10-07'], ['跟进人', 'UAT Operator']],
    attachments: [],
    metrics: [],
    sections: [
      {
        key: 'customer', title: '客户', entity: 'customers', rows: [
          { id: 402, _target_id: 71, _target_entity: 'customers', name: 'Customer name unrelated to IDs', code: 'CUST-ORION', country: 'Germany' },
        ], columns: [],
      },
      { key: 'contact', title: '联系人', entity: 'contacts', rows: [], columns: [] },
    ],
  }
}

async function mountDetail({ entity, id, path, getContext }) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: EmptyPageStub }],
  })
  await router.push(path)
  await router.isReady()
  mocks.api.get.mockImplementation(async url => {
    if (url.startsWith('/context/')) return { data: getContext() }
    if (url === '/session/current-operator/') return { data: { role: '开发超级管理员', name: 'UAT Operator' } }
    if (url === '/operation-logs/') return { data: [] }
    return { data: [] }
  })
  const wrapper = mount(EntityDetailModal, {
    props: { entity, id },
    global: {
      plugins: [router],
      stubs: {
        RelatedCreateModal: RelatedCreateHarness,
        OperationLogPanel: OperationLogStub,
        ProductWorkspace: true,
        SKUPage: true,
      },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('Customer and FollowUp quote shortcuts', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => wrapper?.unmount())

  it('opens the shared quote flow from Customer detail with its numeric ID and cancels in place', async () => {
    const mounted = await mountDetail({
      entity: 'customers', id: 501, path: '/customers?detail=501', getContext: () => customerContext(),
    })
    wrapper = mounted.wrapper

    expect(wrapper.find('h2').text()).toBe('Orion Lighting GmbH')
    await wrapper.findAll('button').find(button => button.text().includes('新建报价')).trigger('click')
    await flushPromises()

    const quoteCreate = wrapper.findComponent(RelatedCreateHarness)
    expect(quoteCreate.exists()).toBe(true)
    expect(quoteCreate.props()).toMatchObject({ entity: 'quotes', query: { customer: 501 } })
    expect(mounted.router.currentRoute.value.fullPath).toBe('/customers?detail=501')
    expect(mocks.api.post).not.toHaveBeenCalled()

    await quoteCreate.find('[data-test="related-close"]').trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(RelatedCreateHarness).exists()).toBe(false)
    expect(wrapper.find('h2').text()).toBe('Orion Lighting GmbH')
    expect(mounted.router.currentRoute.value.fullPath).toBe('/customers?detail=501')
    expect(mocks.api.post).not.toHaveBeenCalled()
  })

  it('does not offer quote creation when the Customer ID is invalid', async () => {
    const mounted = await mountDetail({
      entity: 'customers', id: 'not-an-id', path: '/customers?detail=not-an-id', getContext: () => customerContext(),
    })
    wrapper = mounted.wrapper

    expect(wrapper.findAll('button').some(button => button.text().includes('新建报价'))).toBe(false)
    expect(wrapper.findComponent(RelatedCreateHarness).exists()).toBe(false)
  })

  it('keeps the existing Customer quote-tab create and refreshes the selected tab after save', async () => {
    let contextLoads = 0
    const mounted = await mountDetail({
      entity: 'customers', id: 501, path: '/customers?detail=501',
      getContext: () => customerContext(++contextLoads > 1 ? [{ id: 901, quote_no: 'QT-UAT-0901' }] : []),
    })
    wrapper = mounted.wrapper

    await wrapper.findAll('.detail-tabs button').find(button => button.text().includes('报价记录')).trigger('click')
    await flushPromises()
    await wrapper.findAll('.relation-actions button').find(button => button.text().includes('新增报价')).trigger('click')
    await flushPromises()

    const quoteCreate = wrapper.findComponent(RelatedCreateHarness)
    expect(quoteCreate.props()).toMatchObject({ entity: 'quotes', query: { customer: 501 } })
    await quoteCreate.find('[data-test="related-save"]').trigger('click')
    await flushPromises()

    expect(contextLoads).toBe(2)
    expect(wrapper.find('.detail-tabs button.active').text()).toContain('报价记录')
    expect(wrapper.text()).toContain('QT-UAT-0901')
    expect(wrapper.findComponent(RelatedCreateHarness).exists()).toBe(false)
  })

  it('uses the FollowUp customer relationship ID and cancel preserves due/detail context', async () => {
    const mounted = await mountDetail({
      entity: 'follow-ups', id: 402, path: '/follow-ups?due=true&detail=402', getContext: followUpContext,
    })
    wrapper = mounted.wrapper

    expect(wrapper.text()).toContain('Customer name unrelated to IDs')
    await wrapper.findAll('button').find(button => button.text().includes('新建报价')).trigger('click')
    await flushPromises()

    const quoteCreate = wrapper.findComponent(RelatedCreateHarness)
    expect(quoteCreate.props()).toMatchObject({ entity: 'quotes', query: { customer: 71 } })
    expect(quoteCreate.props().query.customer).not.toBe(402)
    expect(mounted.router.currentRoute.value.fullPath).toBe('/follow-ups?due=true&detail=402')

    await quoteCreate.find('[data-test="related-close"]').trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(RelatedCreateHarness).exists()).toBe(false)
    expect(wrapper.text()).toContain('UAT quote follow-up')
    expect(mounted.router.currentRoute.value.fullPath).toBe('/follow-ups?due=true&detail=402')
    expect(mocks.api.post).not.toHaveBeenCalled()
  })
})
