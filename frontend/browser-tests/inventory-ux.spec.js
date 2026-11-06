import { test, expect } from '@playwright/test'
import { evidencePath, installRepair04Diagnostics } from './r1-repair-04-diagnostics.js'
const longName = '长名称照明灯带产品及完整规格用于库存办公页面验收'.repeat(3)
const skus = Array.from({length:52},(_,i)=>({id:i+1,sku:`SKU-${String(i+1).padStart(3,'0')}`,display_name_cn:longName,product_name:longName,unit:i%2?'pcs':'m',actual_quantity:i===0?0:123456789012,reserved_quantity:i===2?123456789012:i===1?12:0,available_quantity:i===0||i===2?0:i===1?123456789000:123456789012,in_transit_quantity:20,to_procure_quantity:0,trade_units:[]}))
const movement=(i)=>({id:i+1,movement_no:`IM-${i+1}`,sku:1,sku_code:'SKU-001',product_name:longName,movement_date:'2026-10-14',type:i===1?'purchase_in':i===2?'sale_out':'adjust_in',type_display:i===1?'采购入库':i===2?'销售出库':'盘盈入库',quantity:'20',signed_quantity:i===2?'-20':'20',source_type:i===1?'goods_receipt':i===2?'shipment':'manual',is_automatic:i===1||i===2,is_reversed:i===3,warehouse:'默认仓',related_order_nos:['SO-LONG-COMPLETE-20261014-001'],trade_snapshot:{base_unit:'m'},unit_cost:'2'})
async function mock(page,{restricted=false,empty=false,fail=false}={}){
 const state={fail,empty,posts:0,records:Array.from({length:52},(_,i)=>movement(i))}
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname
  if(path.includes('current-operator'))return route.fulfill({json:restricted?{authenticated:true,rbac_enforcement:true,permissions:{inventory:{view:true},skus:{view:true}}}:{authenticated:true,development_superadmin:true,has_all_permissions:true,audit_log_enabled:true}})
  if(path==='/api/skus/inventory-list/')return state.fail?route.fulfill({status:500,json:{detail:'库存服务失败'}}):route.fulfill({json:state.empty?[]:skus})
  if(path==='/api/skus/')return route.fulfill({json:skus})
  if(path==='/api/skus/1/')return route.fulfill({json:skus[0]})
  if(path.endsWith('/inventory-detail/'))return route.fulfill({json:{movements:[movement(0)],orders:[],purchases:[],shipments:[]}})
  if(path==='/api/inventory-movements/')return state.fail?route.fulfill({status:500,json:{detail:'流水服务失败'}}):route.fulfill({json:state.empty?[]:state.records})
  if(path.endsWith('/reverse/')){state.posts++;state.records[0].is_reversed=true;return route.fulfill({json:state.records[0]})}
  if(path.startsWith('/api/context/inventory-movements/'))return route.fulfill({json:{title:'IM-1',subtitle:'2026-10-14 · 盘盈入库',badge:'+20 m',metrics:[],info:[],sections:[]}})
  if(path==='/api/inventory-movements/1/')return route.fulfill({json:state.records[0]})
  return route.fulfill({json:[]})
 });return state
}
async function bounds(page,selectors){
 const result=await page.evaluate(selectors=>({viewport:innerWidth,pageWidth:document.documentElement.scrollWidth,items:selectors.flatMap(s=>[...document.querySelectorAll(s)].map(e=>{const r=e.getBoundingClientRect();return {x:r.x,right:r.right,width:r.width,height:r.height}}))}),selectors)
 expect(result.pageWidth).toBeLessThanOrEqual(result.viewport)
 for(const r of result.items){expect(r.x).toBeGreaterThanOrEqual(0);expect(r.right).toBeLessThanOrEqual(result.viewport+1);expect(r.width).toBeGreaterThan(0);expect(r.height).toBeGreaterThan(0)}
}
test.beforeEach(async({page},testInfo)=>{page.repair04Diagnostics=await installRepair04Diagnostics(page,`inventory-ux-${testInfo.title}`)})
test.afterEach(async({page})=>{await page.repair04Diagnostics?.save()})
for(const width of [1440,1280,1024]){
 test(`inventory overview, reserved quantities and SKU drawer at ${width}`,async({page})=>{
  await page.setViewportSize({width,height:1000});await mock(page);await page.goto('/inventory')
  await expect(page.locator('.inventory-row')).toHaveCount(25)
  await expect(page.locator('.inventory-summary')).toContainText('已预留')
  await bounds(page,['.inventory-summary article','.toolbar .btn','.toolbar .search-box','.table-wrap'])
  await page.locator('.inventory-row').first().click();await expect(page.getByRole('dialog',{name:'库存详情'})).toBeVisible()
  await expect(page.locator('.detail-metrics')).toContainText('已预留');await expect(page.locator('.inventory-semantics')).toContainText('基础单位')
  await bounds(page,['.sku-detail','.detail-metrics button','.detail-filter'])
  expect(await page.locator('.detail-metrics').evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length)).toBe(width>1300?6:3)
  const values=await page.locator('.detail-metrics strong').evaluateAll(es=>es.map(e=>({scroll:e.scrollWidth,client:e.clientWidth})));for(const value of values)expect(value.scroll).toBeLessThanOrEqual(value.client+1)
  const screenshot=evidencePath(`inventory-overview-${width}.png`);if(screenshot)await page.screenshot({path:screenshot,fullPage:true})
 })
 test(`ledger filters, sticky actions and adjustment dialog at ${width}`,async({page})=>{
  await page.setViewportSize({width,height:1000});await mock(page);await page.goto('/inventory-movements')
  await expect(page.locator('.clickable-row')).toHaveCount(25)
  await bounds(page,['.ledger-filters input','.ledger-filters select','.ledger-filters button','.table-wrap'])
  await expect(page.locator('.clickable-row').nth(1)).toContainText('系统自动');await expect(page.locator('.clickable-row').nth(2)).toContainText('-20 m')
  await expect(page.locator('.clickable-row').nth(3).getByTitle('冲销')).toHaveCount(0)
  await page.getByRole('button',{name:'新建库存调整',exact:true}).click();await expect(page.getByRole('dialog',{name:'新建手工库存流水'})).toBeVisible()
  await bounds(page,['.inventory-movement-modal','.movement-grid input','.movement-grid select','.modal-foot button'])
  const screenshot=evidencePath(`inventory-ledger-${width}.png`);if(screenshot)await page.screenshot({path:screenshot,fullPage:true})
  await page.getByRole('button',{name:'取消',exact:true}).click();await expect(page.getByRole('dialog',{name:'新建手工库存流水'})).toHaveCount(0)
 })
}
test('page restoration, detail navigation and browser Back preserve inventory context',async({page})=>{
 await mock(page);await page.goto('/inventory?page=2&sort=sku&direction=asc');await expect(page.locator('.inventory-row').first()).toContainText('SKU-026')
 await page.reload();await expect(page.locator('.inventory-row').first()).toContainText('SKU-026')
 await page.getByRole('button',{name:'上一页',exact:true}).click();await page.locator('.inventory-row').first().click();const source=page.url()
 await page.locator('.inventory-detail-link').first().click();await expect(page.getByRole('dialog',{name:'库存流水详情'})).toBeVisible();await expect(page.locator('.detail-info')).toContainText('+20 m')
 await page.getByRole('button',{name:'关闭详情',exact:true}).click();await expect(page).toHaveURL(/inventory-movements\?sku=1$/)
 await page.evaluate(()=>history.back());await expect(page).toHaveURL(source);await expect(page.getByRole('dialog',{name:'库存详情'})).toBeVisible()
})
test('empty and failed inventories distinguish errors, retry and no records',async({page})=>{
 const state=await mock(page,{fail:true});await page.goto('/inventory');await expect(page.getByRole('alert')).toContainText('服务器暂时不可用',{timeout:15000})
 state.fail=false;state.empty=true;await page.getByRole('button',{name:/重试|重新加载/}).click();await expect(page.locator('.inventory-row')).toHaveCount(0);await expect(page.locator('.inventory-page')).toContainText('暂无')
 await page.goto('/inventory-movements');await expect(page.locator('.clickable-row')).toHaveCount(0)
})
test('restricted UI hides adjustment, reversal and unauthorized cross-module entrances',async({page})=>{
 await mock(page,{restricted:true});await page.goto('/inventory');await expect(page.locator('.inventory-row')).toHaveCount(25)
 await expect(page.locator('.toolbar').getByRole('link',{name:'采购与验货入库'})).toHaveCount(0);await expect(page.locator('.toolbar').getByRole('link',{name:'订单发货'})).toHaveCount(0)
 await page.goto('/inventory-movements');await expect(page.locator('.clickable-row')).toHaveCount(25);await expect(page.getByRole('button',{name:'新建库存调整',exact:true})).toHaveCount(0);await expect(page.getByTitle('冲销',{exact:true})).toHaveCount(0)
})
