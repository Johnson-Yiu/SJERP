import { beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import Dashboard from '../src/views/Dashboard.vue'
import ReportsPage from '../src/views/ReportsPage.vue'
import ReportBlock from '../src/components/reports/ReportBlock.vue'
import { setAccessOperator } from '../src/accessControl'
const api = vi.hoisted(() => ({get:vi.fn()}))
vi.mock('../src/api', () => ({api}))
const catalog={sources:{sales:{label:'销售报表',dimensions:['time','customer','country','category'],dates:{order_date:'订单日期',created_at:'创建时间'},note:'合同金额。'},purchase:{label:'采购报表',dimensions:['time','supplier'],dates:{order_date:'下单日期'}},customers:{label:'客户增长',dimensions:['time','source'],dates:{created_at:'创建时间'}},cash:{label:'现金收支',dimensions:['time','direction','category'],dates:{transaction_date:'发生日期'}}},dimensions:{time:'时间',customer:'客户',country:'国家',category:'产品主分类',supplier:'供应商',source:'来源',direction:'收支方向'},grains:{day:'日',month:'月',year:'年'}}
const report = params => { const second=params.group_by_2; const groups=second?[{dimension:params.group_by,key:'1',label:'国家 1'},{dimension:second,key:'2',label:'长名称验收客户'}]:undefined; return {source:params.source,group_by:params.group_by,group_by_2:second,date_field:params.date_field||'order_date',date_label:'订单日期',comparison:params.comparison||'previous',period:{date_from:params.date_from||'2026-01-01',date_to:params.date_to||'2026-10-14'},comparison_period:{date_from:'2025-01-01',date_to:'2025-10-14'},totals:{amount:'1234567890.12',count:1,quantities:{pcs:'5'}},changes:{amount:null,count:null},rows:[{key:second?'["1","2"]':'1',label:'长名称验收客户',groups,amount:'1234567890.12',count:1,quantities:{pcs:'5'}}],filters:Object.fromEntries(Object.entries(params).filter(([key])=>key.startsWith('filter_')).map(([key,value])=>[key.slice(7),value])),filter_summary:Object.entries(params).filter(([key])=>key.startsWith('filter_')).map(([key,value])=>({dimension:key.slice(7),value,label:key.slice(7)==='country'?'国家 1':'长名称验收客户',name:key.slice(7)==='country'?'国家/地区':'客户'})),note:'测试统计口径'} }
const dashboard=()=>({date_ranges:{as_of:'2026-10-22',year_start:'2026-01-01',year_end:'2026-10-22',trend_start:'2025-11-01',trend_end:'2026-10-22'},summary:{sales_ytd:'1234567890.12',sales_last_ytd:'1234567890.12',orders_ytd:4,active_customers:2,follow_ups_due:1,receipts_rmb:20,payments_rmb:10,certificate_attention:1,certificate_expired:0,certificate_expiring:1},monthly_sales:[{month:'2025-11',sales:100,orders:1},{month:'2026-10',sales:200,orders:1}],category_sales:[],top_customers:[{id:1,name:'长名称验收客户',country:'CN',sales:100,orders:1}],due_follow_ups:[{id:3,next_follow_up:'2026-10-14',customer_name:'客户',subject:'报价跟进',owner:'员工'}],certificate_alerts:[]})
const button=(w,text)=>w.findAll('button').find(b=>b.text()===text)
const field=(w,text)=>w.findAll('label').find(l=>l.text().startsWith(text)).find('input,select')
async function page(component,path='/reports') {
 const router=createRouter({history:createMemoryHistory(),routes:['/','/reports','/finance','/customers','/follow-ups','/orders','/product-certificates'].map(path=>({path,component:{template:'<main />'}}))})
 await router.push(path); await router.isReady(); const wrapper=mount(component,{global:{plugins:[router]}}); await flushPromises(); return {wrapper,router}
}
beforeEach(()=>{vi.resetAllMocks();localStorage.clear();vi.spyOn(window,'scrollTo').mockImplementation(()=>{});api.get.mockImplementation(async(url,{params}={})=>({data:url==='/reports/catalog/'?catalog:url==='/dashboard/'?dashboard():report(params||{})}))})
it('dashboard explains server date ranges, zero change, refresh feedback and retains stale data after refresh failure',async()=>{
 const {wrapper:w}=await page(Dashboard,'/');expect(w.text()).not.toContain('增长线索');expect(w.text()).not.toContain('实时同步');expect(w.text()).toContain('2026-01-01 — 2026-10-22');expect(w.text()).toContain('最近12个自然月（2025-11-01 — 2026-10-22）');expect(w.text()).not.toContain('未来日期订单');expect(w.text()).toContain('0.0% 较去年同期');expect(w.get('a[href="/follow-ups?due=true&detail=3"]').exists()).toBe(true)
 await button(w,'刷新数据').trigger('click');await flushPromises();expect(w.text()).toContain('经营数据已刷新');api.get.mockRejectedValueOnce(new Error('刷新请求失败'));await button(w,'刷新数据').trigger('click');await flushPromises();expect(w.text()).toContain('上一次成功加载的数据');expect(w.text()).toContain('长名称验收客户');expect(w.find('.page-notice').exists()).toBe(false);w.unmount()
})
it('dashboard retries initial failure and hides unavailable module links and metrics',async()=>{
 api.get.mockRejectedValueOnce(new Error('初次加载失败'));const {wrapper:w}=await page(Dashboard,'/');expect(w.find('[role=alert]').text()).toContain('初次加载失败');await w.find('[role=alert] button').trigger('click');await flushPromises()
 setAccessOperator({authenticated:true,rbac_enforcement:true,permissions:{dashboard:{view:true},customers:{view:true}}});await flushPromises();expect(w.find('.chart-panel').exists()).toBe(false);expect(w.text()).toContain('没有订单查看权限');expect(w.find('a[href="/reports"]').exists()).toBe(false);expect(w.text()).not.toContain('本年截至今日销售额');w.unmount()
})
it('drafts wait for submit, stale save is disabled, and submitted query restores from URL',async()=>{
 const {wrapper:w,router}=await page(ReportsPage);const initial=api.get.mock.calls.length;await field(w,'报表预设').setValue('sales-customer');await flushPromises();expect(api.get).toHaveBeenCalledTimes(initial);expect(w.text()).toContain('当前图表仍显示上次查询结果');expect(button(w,'保存为图表块').attributes('disabled')).toBeDefined()
 await field(w,'开始日期').setValue('2026-09-01');await w.get('form.report-controls').trigger('submit');await flushPromises();expect(router.currentRoute.value.query).toMatchObject({group_by:'customer',date_from:'2026-09-01',title:'客户销售排行'});expect(button(w,'保存为图表块').attributes('disabled')).toBeUndefined();const path=router.currentRoute.value.fullPath;w.unmount();const restored=await page(ReportsPage,path);expect(field(restored.wrapper,'统计维度').element.value).toBe('customer');expect(field(restored.wrapper,'开始日期').element.value).toBe('2026-09-01');restored.wrapper.unmount()
})
it('supports a second dimension, preserves it in the URL and drills either group back to the other',async()=>{
 const {wrapper:w,router}=await page(ReportsPage);await field(w,'统计维度').setValue('country');await field(w,'第二统计维度').setValue('customer');await field(w,'图表名称').setValue('国家客户交叉');await w.get('form.report-controls').trigger('submit');await flushPromises();
 expect(router.currentRoute.value.query).toMatchObject({group_by:'country',group_by_2:'customer'});expect(w.findAll('.report-table th').map(th=>th.text())).toEqual(['国家/地区','客户','金额（人民币）','去重单据 / 档案数','数量（按单位）']);await button(w,'保存为图表块').trigger('click');expect(JSON.parse(localStorage.getItem('senju-report-blocks-v1'))[0].config.group_by_2).toBe('customer');expect(w.findAll('.report-link')).toHaveLength(4);expect(api.get).toHaveBeenLastCalledWith('/reports/data/',expect.objectContaining({params:expect.objectContaining({group_by:'country',group_by_2:'customer'})}));
 await w.findAll('.report-table .report-link')[0].trigger('click');await flushPromises();expect(field(w,'统计维度').element.value).toBe('customer');expect(field(w,'第二统计维度').element.value).toBe('');expect(w.get('.filter-chips').text()).toContain('国家：国家 1');expect(router.currentRoute.value.query).toMatchObject({group_by:'customer',filter_country:'1'});
 await button(w,'返回上次分析').trigger('click');await flushPromises();expect(field(w,'统计维度').element.value).toBe('country');expect(field(w,'第二统计维度').element.value).toBe('customer');expect(router.currentRoute.value.query).toMatchObject({group_by:'country',group_by_2:'customer'});w.unmount()
})
it('clears an incompatible second dimension when the source changes and keeps old saved charts compatible',async()=>{
 localStorage.setItem('senju-report-blocks-v1',JSON.stringify([{id:'multi',config:{source:'sales',group_by:'country',group_by_2:'customer',title:'国家客户',filters:{}}},{id:'legacy',config:{source:'sales',group_by:'customer',title:'旧图表',filters:{}}}]))
 const {wrapper:w}=await page(ReportsPage);expect(w.findAll('.saved-block')).toHaveLength(2);await field(w,'统计维度').setValue('country');await field(w,'第二统计维度').setValue('customer');await field(w,'数据来源').setValue('purchase');expect(field(w,'第二统计维度').element.value).toBe('');w.unmount()
})
it('invalid dates suppress requests and date shortcuts only stage dates',async()=>{
 const {wrapper:w}=await page(ReportsPage);const count=api.get.mock.calls.length;await field(w,'开始日期').setValue('2026-12-31');await field(w,'结束日期').setValue('2026-01-01');await w.get('form.report-controls').trigger('submit');await flushPromises();expect(w.find('[role=alert]').text()).toContain('开始日期不能晚于');expect(api.get).toHaveBeenCalledTimes(count);await button(w,'本月至今').trigger('click');await flushPromises();expect(api.get).toHaveBeenCalledTimes(count);w.unmount()
})
it('catalog retry and filter errors retain existing graph, with explicit filter apply',async()=>{
 api.get.mockRejectedValueOnce(new Error('目录失败'));const {wrapper:w}=await page(ReportsPage);await button(w,'重新加载').trigger('click');await flushPromises();expect(w.find('form').exists()).toBe(true);api.get.mockRejectedValueOnce(new Error('选项失败'));await field(w,'筛选维度').setValue('customer');await flushPromises();expect(w.text()).toContain('选项失败');expect(w.find('.report-block .block-kpis').exists()).toBe(true)
 await button(w,'刷新选项').trigger('click');await flushPromises();await field(w,'可用值').setValue('1');await button(w,'添加筛选').trigger('click');expect(w.get('.filter-chips').text()).toContain('长名称验收客户');await w.get('form.report-controls').trigger('submit');await flushPromises();expect(api.get).toHaveBeenLastCalledWith('/reports/data/',expect.objectContaining({params:expect.objectContaining({filter_customer:'1'})}));w.unmount()
})
it('local charts restore, reorder, remove and undo while retaining existing storage key and shared dates',async()=>{
 const {wrapper:w}=await page(ReportsPage);await button(w,'保存为图表块').trigger('click');await flushPromises();await field(w,'报表预设').setValue('sales-customer');await w.get('form.report-controls').trigger('submit');await flushPromises();await button(w,'保存为图表块').trigger('click');await flushPromises();const entries=JSON.parse(localStorage.getItem('senju-report-blocks-v1'));expect(entries).toHaveLength(2);expect(entries[0]).not.toHaveProperty('filter_summary');expect(entries[0].config.filters).not.toHaveProperty('date_from')
 await button(w.findAll('.saved-block')[1],'上移').trigger('click');await flushPromises();expect(JSON.parse(localStorage.getItem('senju-report-blocks-v1'))[0].config.group_by).toBe('customer');await button(w.findAll('.saved-block')[0],'载入查询').trigger('click');await flushPromises();expect(field(w,'统计维度').element.value).toBe('customer');await button(w.findAll('.saved-block')[0],'移除').trigger('click');await flushPromises();expect(w.findAll('.saved-block')).toHaveLength(1);await button(w,'撤销移除').trigger('click');await flushPromises();expect(w.findAll('.saved-block')).toHaveLength(2);w.unmount();const restored=await page(ReportsPage);expect(restored.wrapper.findAll('.saved-block')).toHaveLength(2);restored.wrapper.unmount()
})
it('saved chart drill preserves response period and returns to original results and pending draft',async()=>{
 const {wrapper:w}=await page(ReportsPage);await field(w,'报表预设').setValue('sales-customer');await field(w,'开始日期').setValue('2026-09-01');await w.get('form.report-controls').trigger('submit');await flushPromises();await button(w,'保存为图表块').trigger('click');await flushPromises();await field(w,'开始日期').setValue('2026-10-01');await w.find('.saved-block .report-link').trigger('click');await flushPromises();expect(field(w,'开始日期').element.value).toBe('2026-09-01');expect(w.get('.filter-chips').text()).toContain('长名称验收客户');await button(w,'返回上次分析').trigger('click');await flushPromises();expect(field(w,'开始日期').element.value).toBe('2026-10-01');expect(w.get('.applied-summary').text()).toContain('2026-09-01');expect(w.text()).toContain('当前图表仍显示上次查询结果');w.unmount()
})
it('restricted sources are absent and inaccessible local charts send no report request',async()=>{
 setAccessOperator({authenticated:true,rbac_enforcement:true,permissions:{reports:{view:true},customers:{view:true}}});localStorage.setItem('senju-report-blocks-v1',JSON.stringify([{id:'hidden',config:{source:'sales',group_by:'time',title:'受限图表'}}]));const {wrapper:w}=await page(ReportsPage);expect(field(w,'数据来源').findAll('option').map(o=>o.attributes('value'))).toEqual(['customers']);expect(w.text()).toContain('没有此图表的数据来源');expect(w.find('a[href="/finance"]').exists()).toBe(false);expect(api.get.mock.calls.filter(([url])=>url==='/reports/data/').every(([,config])=>config.params.source==='customers')).toBe(true);expect(w.find('.saved-actions button').attributes('disabled')).toBeDefined();expect(w.find('.block-actions button').exists()).toBe(false);w.unmount()
})
it('storage failure warns instead of claiming persistence',async()=>{
 const {wrapper:w}=await page(ReportsPage);const spy=vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('quota')});await button(w,'保存为图表块').trigger('click');expect(w.text()).toContain('刷新页面后可能丢失本次修改');expect(w.find('.page-notice').exists()).toBe(false);spy.mockRestore();w.unmount()
})
it('export failure retains chart and switching configuration resets the display override',async()=>{
 const {wrapper:w}=await page(ReportBlock);await w.find('.block-actions select').setValue('table');api.get.mockRejectedValueOnce(new Error('导出失败'));await w.find('.block-actions button').trigger('click');await flushPromises();expect(w.text()).toContain('导出失败');expect(w.find('.block-kpis').exists()).toBe(true);await w.setProps({config:{source:'customers',group_by:'time',metric:'count',view:'line'}});await flushPromises();expect(w.find('.block-actions select').element.value).toBe('');expect(w.find('.report-line').exists()).toBe(true);w.unmount()
})
it('an invalid bookmarked filter is rejected and navigating back to valid conditions recovers',async()=>{
 const {wrapper:w,router}=await page(ReportsPage,'/reports?source=sales&filter_warehouse=x')
 expect(w.text()).toContain('附加筛选不适用于');expect(w.find('.report-block').exists()).toBe(false)
 await router.push('/reports?source=sales&group_by=customer&date_field=order_date');await flushPromises()
 expect(w.find('.report-block').exists()).toBe(true);expect(field(w,'统计维度').element.value).toBe('customer');w.unmount()
})
it('changing date scope invalidates in-flight options and cannot offer stale selections',async()=>{
 const {wrapper:w}=await page(ReportsPage);let resolveOld
 api.get.mockImplementationOnce(()=>new Promise(resolve=>{resolveOld=resolve}))
 await field(w,'筛选维度').setValue('customer');await field(w,'开始日期').setValue('2026-09-01')
 resolveOld({data:{rows:[{key:'stale',label:'旧日期客户'}]}});await flushPromises()
 expect(w.text()).not.toContain('旧日期客户');expect(field(w,'可用值').attributes('disabled')).toBeDefined();w.unmount()
})
