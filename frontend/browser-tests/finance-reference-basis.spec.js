import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'
import { evidencePath, installRepair04Diagnostics } from './r1-repair-04-diagnostics.js'
const saved=JSON.parse(readFileSync(new URL('../../docs/uat-evidence/r1-fin-p1/after.json',import.meta.url),'utf8'))
const note=saved.finance.body.cash_basis.note
async function mock(page){await page.route('**/api/**',async route=>{const path=new URL(route.request().url()).pathname;let json=[]
 if(path.includes('current-operator'))json={development_superadmin:true,has_all_permissions:true,authenticated:true}
 else if(path==='/api/finance-dashboard/')json=saved.finance.body
 else if(path==='/api/transactions/')json=saved.transactions.body
 else if(path==='/api/reports/catalog/')json={sources:{cash:{label:'账面收支（人民币折算参考）',dimensions:['time','direction'],dates:{transaction_date:'流水发生日期'},note},sales:{label:'销售报表',dimensions:['time'],dates:{order_date:'订单日期'}}},dimensions:{time:'时间',direction:'收支方向'},grains:{month:'月'}}
 else if(path==='/api/reports/data/')json=saved.cash.body
 await route.fulfill({json})})}
test.beforeEach(async({page},testInfo)=>{page.repair04Diagnostics=installRepair04Diagnostics(page,`finance-reference-basis-${testInfo.title}`)})
test.afterEach(async({page})=>{await page.repair04Diagnostics?.save()})
for(const width of [1440,1024]) test(`reference basis across finance, transactions and saved cash config ${width}`,async({page})=>{
 await page.setViewportSize({width,height:1000});await mock(page)
 await page.goto('/finance');await expect(page.getByText('账面收入（折算参考）',{exact:true})).toBeVisible();await expect(page.locator('main')).toContainText('原币为CNY');await expect(page.locator('main')).not.toContainText('实际收入')
 await page.goto('/transactions');await expect(page.getByRole('columnheader',{name:'人民币折算参考',exact:true})).toBeVisible();await expect(page.locator('main')).toContainText('不代表银行实际到账')
 await page.getByRole('button',{name:'新增记账',exact:true}).click();await expect(page.getByRole('spinbutton',{name:/参考折算汇率/})).toBeVisible();await expect(page.getByRole('dialog')).not.toContainText('结汇汇率');await page.getByRole('button',{name:'取消',exact:true}).click()
 await page.goto('/reports?source=cash&group_by=direction&date_field=transaction_date&title=旧保存净现金流&view=table&metric=amount&date_from=2026-10-01&date_to=2026-10-18')
 await expect(page.getByRole('heading',{name:'旧保存净现金流',exact:true})).toBeVisible();await expect(page.locator('.report-note')).toContainText('账面人民币折算参考');await expect(page.locator('.block-kpis')).toContainText('账面净收支（折算参考）')
 await expect(page.getByRole('columnheader',{name:'金额（人民币折算参考）',exact:true})).toBeVisible();await expect(page.getByRole('combobox',{name:'图表指标',exact:true})).toHaveText(/金额（人民币折算参考）/);await expect(page.locator('main')).not.toContainText('优先使用实际人民币金额')
 const overflow=await page.locator('main').evaluate(el=>el.scrollWidth>el.clientWidth);expect(overflow).toBe(false)
 const screenshot=evidencePath(`finance-reference-basis-${width}.png`);if(screenshot)await page.screenshot({path:screenshot,fullPage:true})
})
