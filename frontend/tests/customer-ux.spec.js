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
    if (url.startsWith('/context/')) return { data: getContext(url) }
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


import { resourceConfigs } from '../src/resourceConfigs'
const related = (key,title,entity,id,label) => ({key,title,entity,columns:[['name','名称']],rows:[{id,name:label,_target_entity:entity,_target_id:id}]})
const customerUX = () => ({...customerContext(),metrics:[['累计销售额',12,'rmb'],['订单',1,'number'],['报价',1,'number'],['下次跟进','2026-10-10','date']],sections:[related('followups','跟进记录','follow-ups',7,'Recent followup'),related('quotes','报价记录','quotes',45,'QT-45'),related('orders','订单','orders',46,'SO-46'),related('contacts','联系人','contacts',47,'UX Contact'),related('purchases','成交商品记录','orders',46,'Sold SKU'),related('cash','财务流水','transactions',48,'TX-48')]})
function nestedUX(entity,id) { return {entity,title:`${entity}-${id}`,info:[],metrics:[],sections:[related('items',entity==='quotes'?'报价明细':'订单明细','skus',99,'Actual line'),related('customer','客户','customers',501,'UX Buyer')]} }
describe('Customer UX hierarchy and navigation',()=>{
 let wrapper
 afterEach(()=>wrapper?.unmount())
 beforeEach(()=>vi.clearAllMocks())
 async function detail(){const result=await mountDetail({entity:'customers',id:501,path:'/customers?detail=501',getContext:url=>url.includes('/customers/')?customerUX():url.includes('/quotes/')?nestedUX('quotes',45):url.includes('/orders/')?nestedUX('orders',46):nestedUX('contacts',47)});wrapper=result.wrapper;return result}
 async function click(text){await wrapper.findAll('button').find(b=>b.text().includes(text)).trigger('click');await flushPromises()}
 it('customer columns follow daily recognition priority',()=>expect(resourceConfigs.customers.columns.map(c=>c[0])).toEqual(['name','code','status','country','region','owner','next_follow_up','order_count','sales_amount']))
 it('defaults to followup and shows summary/actions/edit event',async()=>{await detail();expect(wrapper.get('.detail-tabs button.active').text()).toContain('跟进记录');expect(wrapper.text()).toContain('客户业务记录');expect(wrapper.findAll('.detail-metrics small').map(e=>e.text())).toEqual(['累计销售额','订单','报价','下次跟进']);await click('编辑客户');expect(wrapper.emitted('edit')).toHaveLength(1)})
 it('adds followup through shared related editor with current customer and cancels',async()=>{await detail();await click('新增跟进');expect(wrapper.findComponent(RelatedCreateHarness).props()).toMatchObject({entity:'follow-ups',query:{customer:501}});await wrapper.get('[data-test="related-close"]').trigger('click');await flushPromises();expect(wrapper.findComponent(RelatedCreateHarness).exists()).toBe(false);expect(mocks.api.post).not.toHaveBeenCalled()})
 it('retains quote shortcut prefill',async()=>{await detail();await click('新建报价');expect(wrapper.findComponent(RelatedCreateHarness).props()).toMatchObject({entity:'quotes',query:{customer:501}})})
 it.each([['报价记录','quotes',45,'报价明细','打开报价工作台'],['订单','orders',46,'订单明细','打开订单工作台']])('drills %s lines first, exact workbench and browser back',async(tab,entity,id,section,label)=>{const {router}=await detail();await click(tab);await wrapper.get('tbody tr').trigger('click');await flushPromises();expect(wrapper.get('.detail-tabs button.active').text()).toContain(section);expect(wrapper.text()).toContain('Actual line');const link=wrapper.findAll('a').find(a=>a.text().includes(label));expect(link.attributes('href')).toBe(`/${entity}?detail=${id}`);await click('返回');expect(wrapper.get('h2').text()).toBe('Orion Lighting GmbH');await click(tab);await wrapper.get('tbody tr').trigger('click');await flushPromises();await wrapper.findAll('a').find(a=>a.text().includes(label)).trigger('click');await flushPromises();expect(router.currentRoute.value.fullPath).toBe(`/${entity}?detail=${id}`);expect(wrapper.emitted('close')).toBeUndefined();router.back();await new Promise(resolve=>setTimeout(resolve,0));await flushPromises();expect(router.currentRoute.value.fullPath).toBe('/customers?detail=501')})
 it('sold items still drill to their order',async()=>{await detail();await click('成交商品记录');await wrapper.get('tbody tr').trigger('click');await flushPromises();expect(wrapper.get('h2').text()).toBe('orders-46')})
 it('other nested entities keep standard management link',async()=>{await detail();await click('联系人');await wrapper.get('tbody tr').trigger('click');await flushPromises();const link=wrapper.findAll('a').find(a=>a.text().includes('打开管理页'));expect(link.attributes('href')).toBe('/contacts')})
})
