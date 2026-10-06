// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
const mocks = vi.hoisted(() => ({ api: { get: vi.fn() }, listAll: vi.fn() }))
vi.mock('../src/api', () => mocks)
import ResourcePage from '../src/views/ResourcePage.vue'
import Dashboard from '../src/views/Dashboard.vue'
import CertificateExpiryBadge from '../src/components/CertificateExpiryBadge.vue'
import { resourceConfigs } from '../src/resourceConfigs'
import { certificateFilterQuery } from '../src/utils/certificateExpiry'

let wrappers = []
afterEach(() => { wrappers.forEach(w => w.unmount()); wrappers = [] })
beforeEach(() => { vi.clearAllMocks(); mocks.listAll.mockResolvedValue([]) })
async function page(url='/product-certificates', component=ResourcePage) {
  const router = createRouter({ history:createMemoryHistory(), routes:[{path:'/:pathMatch(.*)*', component}] })
  await router.push(url); await router.isReady()
  const wrapper = mount(component, { props:component === ResourcePage ? {config:resourceConfigs['product-certificates']} : {}, global:{plugins:[router],stubs:{SummaryCards:true,EntityDetailModal:{props:['id'],template:'<aside data-test="detail">{{ id }}</aside>'}}} })
  wrappers.push(wrapper); await flushPromises()
  return { wrapper, router }
}
async function click(w,label) { await w.findAll('button').find(b=>b.text()===label).trigger('click'); await flushPromises() }
describe('certificate expiry badges from server', () => {
  it.each([['expired',-35,'已过期 · 35 天'],['expiring_30',0,'今日到期'],['expiring_30',7,'7 天后到期'],['expiring_90',45,'45 天后到期'],['valid',91,'有效'],['no_expiry',null,'无有效期']])('%s %s', (status,days,text) => {
    const w = mount(CertificateExpiryBadge,{props:{certificate:{expiry_status:status,days_to_expiry:days}}}); wrappers.push(w)
    expect(w.text()).toBe(text); expect(w.classes()).toContain(status)
  })
})
describe('certificate list routes', () => {
  it('renders server badge in certificate table', async () => {
    mocks.listAll.mockResolvedValue([{id:1,name:'CE',expiry_status:'expired',days_to_expiry:-35}])
    const {wrapper} = await page(); expect(wrapper.text()).toContain('有效状态'); expect(wrapper.text()).toContain('已过期 · 35 天')
  })
  it('direct mount keeps active attention filter and sends backend parameter', async () => {
    const {wrapper} = await page('/product-certificates?expiry=attention')
    expect(mocks.listAll).toHaveBeenCalledWith('/product-certificates/',{params:{expiry:'attention',search:''}})
    expect(wrapper.findAll('button').find(b=>b.text()==='需关注').attributes('aria-pressed')).toBe('true')
    expect(wrapper.text()).toContain('需要关注的证书')
  })
  it('quick filters update URL, reload server scope, and preserve product context', async () => {
    const {wrapper,router} = await page('/product-certificates?product=12')
    for (const [label,value] of [['需关注','attention'],['已过期','expired'],['90 天内到期','expiring'],['无有效期','no_expiry']]) {
      await click(wrapper,label); expect(router.currentRoute.value.query).toEqual({product:'12',expiry:value})
      expect(mocks.listAll).toHaveBeenLastCalledWith('/product-certificates/',{params:{product:'12',expiry:value,search:''}})
    }
    await click(wrapper,'全部'); expect(router.currentRoute.value.query).toEqual({product:'12'})
  })
  it('clear removes only expiry and keeps exact detail mounted', async () => {
    const {wrapper,router} = await page('/product-certificates?product=12&expiry=attention&detail=8')
    expect(wrapper.get('[data-test="detail"]').text()).toBe('8')
    expect(mocks.listAll).toHaveBeenCalledWith('/product-certificates/',{params:{product:'12',expiry:'attention',search:''}})
    await click(wrapper,'清除筛选')
    expect(router.currentRoute.value.query).toEqual({product:'12',detail:'8'})
    expect(wrapper.get('[data-test="detail"]').text()).toBe('8')
  })
  it('pure clear helper preserves other query values', () => expect(certificateFilterQuery({expiry:'expired',detail:'8',search:'CE'},'')).toEqual({detail:'8',search:'CE'}))
})
const dashboard = count => ({summary:{certificate_attention:count,certificate_expired:1,certificate_expiring:2},monthly_sales:[],category_sales:[],top_customers:[],due_follow_ups:[],certificate_alerts:count?[{id:8,product_name:'UAT Light',certificate_name:'CE',certificate_no:'CE-8',expires_on:'2026-10-06',expiry_status:'expired',days_to_expiry:-1}]:[]})
describe('dashboard certificate reminders', () => {
  it('shows counts, urgent row, all and exact detail destinations', async () => {
    mocks.api.get.mockResolvedValue({data:dashboard(3)})
    const {wrapper} = await page('/',Dashboard)
    const section = wrapper.get('[aria-label="证书到期提醒"]')
    expect(section.text()).toContain('需关注 3 个，其中已过期 1 个')
    expect(section.text()).toContain('90 天内到期 2 个')
    expect(section.text()).toContain('UAT Light'); expect(section.text()).toContain('CE-8'); expect(section.text()).toContain('已过期 · 1 天')
    expect(section.findAll('a').map(a=>a.attributes('href'))).toEqual(['/product-certificates?expiry=attention','/product-certificates?expiry=attention&detail=8'])
  })
  it('zero risk displays neutral healthy state', async () => {
    mocks.api.get.mockResolvedValue({data:dashboard(0)})
    const {wrapper} = await page('/',Dashboard)
    const section=wrapper.get('[aria-label="证书到期提醒"]')
    expect(section.text()).toContain('当前没有 90 天内到期的证书'); expect(section.find('.expired').exists()).toBe(false)
  })
})
