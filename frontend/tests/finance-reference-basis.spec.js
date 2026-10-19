// @vitest-environment jsdom
import {it,expect,vi,afterEach} from 'vitest'
import {mount,flushPromises} from '@vue/test-utils'
import {createRouter,createMemoryHistory} from 'vue-router'
import FinanceDashboardPage from '../src/views/FinanceDashboardPage.vue'
import TransactionPage from '../src/views/TransactionPage.vue'
import ReportBlock from '../src/components/reports/ReportBlock.vue'
const mocks=vi.hoisted(()=>({api:{get:vi.fn()},listAll:vi.fn()}))
vi.mock('../src/api',()=>mocks)
let w
afterEach(()=>{w?.unmount();vi.clearAllMocks()})
async function view(component,path,props={}){const router=createRouter({history:createMemoryHistory(),routes:[path].map(path=>({path,component:{template:'<div />'}}))});await router.push(path);w=mount(component,{props,global:{plugins:[router]}});await flushPromises();return router}
it('legacy dashboard response retains amounts but makes the basis and dates explicit',async()=>{
 mocks.api.get.mockResolvedValue({data:{metrics:{income_rmb:'249.2346',expense_rmb:'16.6689',net_cash_rmb:'232.5657'},period:{date_from:'2026-09-01',date_to:'2026-09-30'},due_items:[],categories:[],monthly_cash:[]}})
 await view(FinanceDashboardPage,'/finance');expect(w.text()).toContain('账面收入（折算参考）');expect(w.text()).toContain('249.23');expect(w.text()).toContain('232.57');expect(w.text()).toContain('原币为CNY');expect(w.text()).toContain('流水发生日期不等同于银行到账日');expect(w.text()).not.toContain('实际收入')
})
it('actual cash failure does not block the legacy dashboard and retries independently', async()=>{
 let attempts=0
 mocks.api.get.mockImplementation(url=>{
  if(url==='/finance-dashboard/') return Promise.resolve({data:{metrics:{income_rmb:'249.2346'},period:{date_from:'2026-09-01',date_to:'2026-09-30'},due_items:[],categories:[],monthly_cash:[]}})
  if(url==='/actual-rmb-cash/') return attempts++===0 ? Promise.reject(new Error('bank endpoint offline')) : Promise.resolve({data:{basis:'bank_cash_confirmed_v1',period:{date_from:'2026-09-01',date_to:'2026-09-30'},totals:{inflow:'705.00',outflow:'0.00',net:'705.00',count:1},monthly:[],by_kind:[],events:[],note:'已登记银行资金汇总'}})
  return Promise.resolve({data:{}})
 })
 await view(FinanceDashboardPage,'/finance')
 expect(w.text()).toContain('249.23')
 expect(w.text()).toContain('重新加载')
 await w.findAll('button').find(button=>button.text()==='重新加载').trigger('click')
 await flushPromises()
 expect(w.text()).toContain('705.00')
})
it('stale actual cash responses cannot replace the selected period', async()=>{
 const pending=[]
 const actual=amount=>({data:{basis:'bank_cash_confirmed_v1',period:{date_from:'2026-09-01',date_to:'2026-09-30'},totals:{inflow:amount,outflow:'0.00',net:amount,count:1},monthly:[],by_kind:[],events:[],note:'已登记银行资金汇总'}})
 mocks.api.get.mockImplementation(url=>{
  if(url==='/finance-dashboard/') return Promise.resolve({data:{metrics:{},period:{date_from:'2026-09-01',date_to:'2026-09-30'},due_items:[],categories:[],monthly_cash:[]}})
  if(url==='/actual-rmb-cash/') return pending.length===0 ? new Promise(resolve=>pending.push(resolve)) : Promise.resolve(actual('200.00'))
  return Promise.resolve({data:{}})
 })
 const router=await view(FinanceDashboardPage,'/finance')
 const dates=w.findAll('.report-filters input[type="date"]')
 await dates[0].setValue('2026-09-01'); await dates[1].setValue('2026-09-30'); await w.find('.report-filters').trigger('submit'); await flushPromises(); await flushPromises()
 expect(w.text()).toContain('200.00')
 pending[0](actual('100.00')); await flushPromises()
 expect(w.text()).toContain('200.00')
 expect(w.text()).not.toContain('100.00')
 expect(router.currentRoute.value.query).toMatchObject({date_from:'2026-09-01',date_to:'2026-09-30'})
})
it('transaction amount column and rate input clarify reference without changing defaults',async()=>{
 mocks.listAll.mockResolvedValue([]);mocks.api.get.mockResolvedValue({data:[]})
 await view(TransactionPage,'/transactions');expect(w.text()).toContain('账面人民币折算参考');expect(w.findAll('th').map(x=>x.text())).toContain('人民币折算参考')
 await w.findAll('button').find(b=>b.text()==='新增记账').trigger('click');await flushPromises()
 const label=w.findAll('label').find(x=>x.text().includes('参考折算汇率'));expect(label.get('input').element.value).toBe('1');expect(w.text()).not.toContain('结汇汇率')
})
it('saved cash config keeps its title/query and signed values with an unconditional reference note',async()=>{
 mocks.api.get.mockResolvedValue({data:{date_label:'发生日期',period:{date_from:'2026-09-01',date_to:'2026-09-30'},comparison_period:{date_from:'2026-08-01',date_to:'2026-08-31'},totals:{amount:'-16.6689',count:1,quantities:{}},changes:{amount:null},rows:[{key:'expense',label:'支出',amount:'-16.6689',count:1,quantities:{}}],note:'旧API说明'}})
 const config={title:'旧自定义净现金流',source:'cash',group_by:'direction',date_field:'transaction_date',view:'table'}
 await view(ReportBlock,'/reports',{config});expect(w.get('h2').text()).toBe(config.title);expect(mocks.api.get.mock.calls[0][1].params).toMatchObject({source:'cash',date_field:'transaction_date'})
 expect(w.text()).toContain('原币为CNY');expect(w.text()).toContain('账面净收支（折算参考）');expect(w.text()).toContain('-16.67');expect(w.findAll('th').map(x=>x.text())).toContain('金额（人民币折算参考）')
})
