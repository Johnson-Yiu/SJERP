import {test,expect} from '@playwright/test'
import {mockApi,longName} from './reporting-fixtures'
async function bounds(page,selectors){
 const result=await page.evaluate(selectors=>({viewport:innerWidth,pageWidth:document.documentElement.scrollWidth,items:selectors.flatMap(selector=>[...document.querySelectorAll(selector)].map(e=>{const r=e.getBoundingClientRect();return {selector,x:r.x,right:r.right,width:r.width,height:r.height,scroll:e.scrollWidth,client:e.clientWidth}}))}),selectors)
 expect(result.pageWidth).toBeLessThanOrEqual(result.viewport)
 for(const r of result.items){expect(r.x).toBeGreaterThanOrEqual(0);expect(r.right).toBeLessThanOrEqual(result.viewport+1);expect(r.width).toBeGreaterThan(0);expect(r.height).toBeGreaterThan(0)}
 return result
}
for(const width of [1440,1280,1024,700]){
 test(`dashboard long names, large amounts and 12-month layout at ${width}`,async({page})=>{
  await page.setViewportSize({width,height:1000});await mockApi(page);await page.goto('/')
  await expect(page.getByRole('heading',{name:'销售与客户',exact:true})).toBeVisible()
  await expect(page.getByText('最近12个自然月（2025-11-01 — 2026-10-22）· 人民币',{exact:true})).toBeVisible()
  await expect(page.getByText('本年截至今日订单数',{exact:true})).toBeVisible()
  await expect(page.getByText('含未来日期订单',{exact:true})).toHaveCount(0)
  await expect(page.locator('.metric-card.featured strong')).toHaveText('¥ 123,456,789,012.12')
  await bounds(page,['.metric-card','.dash-grid .panel','.dash-bottom .panel','.certificate-reminders','.cash-strip'])
  const textWidths=await page.locator('.metric-card strong,.category-meta strong,.customer-item .grow strong').evaluateAll(elements=>elements.map(e=>({scroll:e.scrollWidth,client:e.clientWidth})));for(const text of textWidths)expect(text.scroll).toBeLessThanOrEqual(text.client+1)
  expect(await page.locator('.metric-grid').evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length)).toBe(width>1300?4:2)
  await page.locator('.certificate-reminders').scrollIntoViewIfNeeded();await bounds(page,['.certificate-item'])
  await page.getByRole('button',{name:'刷新数据',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'经营数据已刷新'})).toBeVisible()
  await page.getByRole('navigation',{name:'经营快捷入口'}).getByRole('link',{name:'报表中心',exact:true}).click();await expect(page).toHaveURL(/\/reports/);await page.goBack();await expect(page.getByRole('heading',{name:'销售与客户',exact:true})).toBeVisible()
 })
 test(`reports complex filters, multi charts and computed layout at ${width}`,async({page})=>{
  await page.setViewportSize({width,height:1000});await mockApi(page)
  await page.addInitScript(()=>localStorage.setItem('senju-report-blocks-v1:4242',JSON.stringify(Array.from({length:6},(_,i)=>({id:'legacy-'+i,config:{source:'sales',group_by:'customer',metric:'amount',view:['bar','line','donut'][i%3],title:'原有图表 '+i,filters:{filter_country:'CN'}}})))))
  await page.goto('/reports');await expect(page.locator('.saved-block')).toHaveCount(6)
  await page.getByRole('combobox',{name:'报表预设',exact:true}).selectOption('sales-customer');await page.getByRole('combobox',{name:'筛选维度',exact:true}).selectOption('customer');await expect(page.getByRole('combobox',{name:'可用值',exact:true})).toBeEnabled();await page.getByRole('combobox',{name:'可用值',exact:true}).selectOption('1');await page.getByRole('button',{name:'添加筛选',exact:true}).click()
  await expect(page.getByRole('button',{name:'保存为图表块',exact:true})).toBeDisabled();await page.getByRole('button',{name:'查询报表',exact:true}).click();await expect(page).toHaveURL(/filter_customer=1/)
  await bounds(page,['form.report-controls','.report-control-grid input','.report-control-grid select','.dimension-filter select','.dimension-filter button','.filter-chips button','.report-block','.report-bar-row'])
  const cols=await page.locator('.report-control-grid').first().evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length);expect(cols).toBe(width>1100?5:2)
  await expect(page.locator('.reports-page > .report-block .block-kpis').first()).toContainText('123,456,789,012.12')
  await expect(page.getByRole('button',{name:'保存为图表块',exact:true})).toBeEnabled();await page.getByRole('button',{name:'保存为图表块',exact:true}).click();await expect(page.locator('.saved-block')).toHaveCount(7)
 })
}
test('saved local chart configurations survive reload, reorder, remove and undo',async({page})=>{
 await mockApi(page);await page.goto('/reports');await expect(page.getByRole('button',{name:'保存为图表块',exact:true})).toBeEnabled();await page.getByRole('button',{name:'保存为图表块',exact:true}).click()
 await page.getByRole('combobox',{name:'报表预设',exact:true}).selectOption('sales-customer');await page.getByRole('textbox',{name:'图表名称',exact:true}).fill('客户验收图');await page.getByRole('button',{name:'查询报表',exact:true}).click();await page.getByRole('button',{name:'保存为图表块',exact:true}).click();await expect(page.locator('.saved-block')).toHaveCount(2)
 await page.locator('.saved-block').nth(1).getByRole('button',{name:'上移',exact:true}).click();await expect(page.locator('.saved-block').first()).toContainText('客户验收图')
 await page.reload();await expect(page.locator('.saved-block')).toHaveCount(2);await expect(page.locator('.saved-block').first()).toContainText('客户验收图')
 await page.locator('.saved-block').first().getByRole('button',{name:'移除',exact:true}).click();await expect(page.locator('.saved-block')).toHaveCount(1);await page.getByRole('button',{name:'撤销移除',exact:true}).click();await expect(page.locator('.saved-block')).toHaveCount(2)
 await page.locator('.saved-block').first().getByRole('button',{name:'载入查询',exact:true}).click();await expect(page.getByRole('combobox',{name:'统计维度',exact:true})).toHaveValue('customer')
})
test('CSV export keeps the last submitted filters while the form has an unsaved draft',async({page})=>{
 await page.setViewportSize({width:1440,height:1000})
 const state=await mockApi(page);await page.goto('/reports')
 await page.getByRole('combobox',{name:'报表预设',exact:true}).selectOption('sales-customer')
 await page.getByRole('combobox',{name:'筛选维度',exact:true}).selectOption('customer')
 await page.getByRole('combobox',{name:'可用值',exact:true}).selectOption('1')
 await page.getByRole('button',{name:'添加筛选',exact:true}).click()
 const [submittedResponse]=await Promise.all([
  page.waitForResponse(response=>{const url=new URL(response.url());return url.pathname==='/api/reports/data/' && url.searchParams.get('filter_customer')==='1' && !url.searchParams.has('export')}),
  page.getByRole('button',{name:'查询报表',exact:true}).click(),
 ])
 expect(submittedResponse.status()).toBe(200)
 await expect(page.getByRole('region',{name:'已查询条件'})).toContainText('客户：')
 await expect(page.getByRole('button',{name:'导出 CSV',exact:true})).toBeVisible()
 const submittedRequest=new URL(submittedResponse.url()).searchParams;expect(submittedRequest.get('filter_customer')).toBe('1')

 await page.getByRole('combobox',{name:'可用值',exact:true}).selectOption('2')
 await page.getByRole('button',{name:'添加筛选',exact:true}).click()
 await expect(page.getByRole('button',{name:'保存为图表块',exact:true})).toBeDisabled()
 await page.getByRole('button',{name:'导出 CSV',exact:true}).click()
 await expect.poll(()=>state.reportRequests.at(-1)?.get('export')).toBe('csv')
 const exportRequest=state.reportRequests.at(-1)
 expect(exportRequest.get('filter_customer')).toBe('1')
 expect(exportRequest.get('filter_customer')).not.toBe('2')
 await page.screenshot({path:'../docs/uat-evidence/r1-prelaunch-consolidation-20261104/closeout-logs/reports-unsaved-filter-1440.png',fullPage:true})
})
test('drill and previous-analysis return preserve actual period and browser navigation restores URL',async({page})=>{
 await mockApi(page);await page.goto('/reports');await page.getByRole('combobox',{name:'报表预设',exact:true}).selectOption('sales-customer');await page.getByRole('textbox',{name:'开始日期',exact:true}).fill('2026-09-01');await page.getByRole('button',{name:'查询报表',exact:true}).click();await expect(page).toHaveURL(/date_from=2026-09-01/)
 await page.getByRole('textbox',{name:'开始日期',exact:true}).fill('2026-10-01');await page.locator('.reports-page > .report-block .report-link').first().click();await expect(page.getByRole('textbox',{name:'开始日期',exact:true})).toHaveValue('2026-09-01');await expect(page).toHaveURL(/filter_customer=1/)
 await page.getByRole('button',{name:'返回上次分析',exact:true}).click();await expect(page.getByRole('textbox',{name:'开始日期',exact:true})).toHaveValue('2026-10-01');await expect(page.getByRole('region',{name:'已查询条件'})).toContainText('2026-09-01')
 await page.getByRole('navigation').first().getByRole('link',{name:'经营概览',exact:true}).click();await expect(page).toHaveURL(/\/$/);await page.goBack();await expect(page.getByRole('textbox',{name:'开始日期',exact:true})).toHaveValue('2026-10-01');await expect(page.getByRole('region',{name:'已查询条件'})).toContainText('2026-09-01');await expect(page).toHaveURL(/date_from=2026-09-01/)
})
test('empty dashboard and charts have useful neutral states',async({page})=>{
 await mockApi(page,{empty:true});await page.goto('/');await expect(page.getByText('暂无月度销售数据。',{exact:true})).toBeVisible();await expect(page.getByText('暂无分类销售数据。',{exact:true})).toBeVisible();await page.goto('/reports');await expect(page.locator('.report-empty')).toContainText('暂无数据');await expect(page.locator('.report-table')).toHaveCount(0)
})
test('initial failures recover, refresh failure keeps stale data, and catalog has retry',async({page})=>{
 const state=await mockApi(page,{failDashboard:true});await page.goto('/');await expect(page.getByRole('alert')).toContainText('经营数据暂不可用');state.failDashboard=false;await page.getByRole('button',{name:'重新加载',exact:true}).click();await expect(page.locator('.metric-card')).toHaveCount(4)
 state.failDashboard=true;await page.getByRole('button',{name:'刷新数据',exact:true}).click();await expect(page.getByRole('alert')).toContainText('上一次成功加载的数据');await expect(page.locator('.metric-card')).toHaveCount(4)
 state.failCatalog=true;await page.goto('/reports');await expect(page.getByRole('alert')).toContainText('报表选项暂不可用');state.failCatalog=false;await page.getByRole('button',{name:'重新加载',exact:true}).click();await expect(page.getByRole('form',{name:'报表查询'})).toBeVisible()
 state.failReport=true;await page.getByRole('button',{name:'查询报表',exact:true}).click();await expect(page.locator('.report-block [role=alert]')).toContainText('报表数据暂不可用');state.failReport=false;await page.locator('.report-block').getByRole('button',{name:'重试',exact:true}).click();await expect(page.locator('.block-kpis')).toBeVisible()
})
test('restricted UI hides sources, export and navigation, retaining unavailable local configuration',async({page})=>{
 const state=await mockApi(page,{restricted:true});await page.addInitScript(()=>localStorage.setItem('senju-report-blocks-v1:4242',JSON.stringify([{id:'restricted-legacy',config:{source:'sales',group_by:'time',title:'原销售图'}}])))
 await page.goto('/');await expect(page.locator('.dashboard-shortcuts a[href="/finance"]')).toHaveCount(0);await expect(page.locator('.metric-card.featured')).toHaveCount(0)
 await page.goto('/reports');await expect(page.getByRole('combobox',{name:'数据来源'}).locator('option')).toHaveCount(1);await expect(page.getByRole('combobox',{name:'数据来源'})).toHaveValue('customers');await expect(page.getByRole('button',{name:'导出 CSV',exact:true})).toHaveCount(0)
 await expect(page.locator('.saved-block')).toContainText('当前账号没有此报表的数据权限，未加载该报表。');expect(state.reportRequests.every(params=>params.get('source')==='customers')).toBe(true)
})
test('two-level groups show separate columns, drill either dimension and return the original query',async({page})=>{
 await mockApi(page);await page.goto('/reports');await page.getByRole('combobox',{name:'统计维度',exact:true}).selectOption('country');await page.getByRole('combobox',{name:'第二统计维度（可选）',exact:true}).selectOption('customer');await page.getByRole('textbox',{name:'图表名称',exact:true}).fill('国家客户交叉');await page.getByRole('button',{name:'查询报表',exact:true}).click();await expect(page).toHaveURL(/group_by_2=customer/);await expect(page.locator('.report-table th')).toHaveCount(6);await expect(page.locator('.report-table th').nth(0)).toHaveText('国家/地区');await expect(page.locator('.report-table th').nth(1)).toHaveText('客户');await expect(page.locator('.report-table .report-link')).toHaveCount(30)
 await page.locator('.report-table .report-link').nth(0).click();await expect(page.getByRole('combobox',{name:'统计维度',exact:true})).toHaveValue('customer');await expect(page.getByRole('combobox',{name:'第二统计维度（可选）',exact:true})).toHaveValue('');await expect(page).toHaveURL(/filter_country=1/);await expect(page.getByRole('button',{name:'返回上次分析',exact:true})).toBeVisible();await page.getByRole('button',{name:'返回上次分析',exact:true}).click();await expect(page.getByRole('combobox',{name:'统计维度',exact:true})).toHaveValue('country');await expect(page.getByRole('combobox',{name:'第二统计维度（可选）',exact:true})).toHaveValue('customer');await expect(page).toHaveURL(/group_by_2=customer/)
})
test('cross-group result opens paginated raw detail and links to the original order',async({page})=>{
 const state=await mockApi(page);await page.goto('/reports');await page.getByRole('combobox',{name:'统计维度',exact:true}).selectOption('country');await page.getByRole('combobox',{name:'第二统计维度（可选）',exact:true}).selectOption('customer');await page.getByRole('button',{name:'查询报表',exact:true}).click();await page.getByRole('button',{name:'查看构成明细',exact:true}).first().click();await expect(page.locator('.report-detail-panel')).toContainText('SO-DETAIL-1');await expect(page.locator('.report-detail-panel')).toContainText('历史商品名称');await expect(page.locator('.report-detail-panel')).toContainText('明细记录 3 条');await expect(page.locator('.report-detail-panel a[href*="/orders"]')).toHaveCount(1);expect(state.detailRequests.at(-1).get('group_by_2')).toBe('customer');await page.getByRole('button',{name:'收起明细',exact:true}).click();await expect(page.locator('.report-detail-panel')).toHaveCount(0)
})
