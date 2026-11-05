import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
const dir=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
  ? path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'finance-csv-stability')
  : path.resolve('../docs/uat-evidence/export-stability-closeout-20261105/finance')
fs.mkdirSync(dir,{recursive:true})
for(const width of [1440,390]) test(`CSV retry and changing period ${width}`,async({page})=>{
 await page.setViewportSize({width,height:900}); let count=0, release; const gate=new Promise(r=>release=r)
 await page.route('**/api/**',async route=>{const u=new URL(route.request().url()), from=u.searchParams.get('date_from'),to=u.searchParams.get('date_to');
 if(u.pathname.includes('current-operator')) return route.fulfill({json:{authenticated:true,development_superadmin:true,has_all_permissions:true}})
 if(['/api/finance-dashboard/','/api/actual-rmb-cash/'].includes(u.pathname)) {
 if(u.searchParams.has('export')) {count++; if(count===1)return route.fulfill({status:400,body:'failed'}); if(count===2)await gate; return route.fulfill({contentType:'text/csv',body:'\ufeff期间,金额\r\n'+from+',42\r\n'})}
 if(u.pathname.includes('dashboard'))return route.fulfill({json:{period:{date_from:from,date_to:to},metrics:{},due_items:[],monthly_cash:[],categories:[]}})
 return route.fulfill({json:{basis:'bank_cash_confirmed_v1',period:{date_from:from,date_to:to},totals:{inflow:'0',outflow:'0',net:'0',count:0},monthly:[],by_kind:[],events:[]}})} return route.fulfill({json:[]})})
 await page.goto('/finance?date_from=2026-10-01&date_to=2026-10-19'); const button=page.getByRole('button',{name:'导出 CSV',exact:true}); await expect(button).toBeEnabled(); await page.screenshot({path:path.join(dir,`finance-${width}.png`),fullPage:true})
 await button.click(); await expect(page.getByRole('alert').first()).toBeVisible(); await expect(button).toBeEnabled(); await button.click(); await expect(page.getByRole('button',{name:'正在导出…'})).toBeDisabled()
 await page.getByLabel('开始日期').fill('2026-09-01'); await page.getByLabel('结束日期').fill('2026-09-30'); await page.getByRole('button',{name:'查询',exact:true}).click(); await expect(page).toHaveURL(/2026-09-30/)
 const downloading=page.waitForEvent('download'); release(); const download=await downloading; expect(download.suggestedFilename()).toContain('2026-10-01-2026-10-19'); const bytes=fs.readFileSync(await download.path()); expect(bytes.subarray(0,3)).toEqual(Buffer.from([239,187,191])); expect(bytes.toString()).toContain('2026-10-01,42')
 const again=page.waitForEvent('download'); await button.click(); expect((await again).suggestedFilename()).toContain('2026-09-01-2026-09-30'); await page.goto('/transactions'); await page.goto('/finance?date_from=2026-09-01&date_to=2026-09-30'); await expect(button).toBeEnabled()
})

test('actual cash export failure can retry and blocks duplicate pending requests',async({page})=>{
 let count=0, release; const gate=new Promise(r=>release=r)
 await page.route('**/api/**',async route=>{const u=new URL(route.request().url()),period={date_from:u.searchParams.get('date_from'),date_to:u.searchParams.get('date_to')};
 if(u.pathname.includes('current-operator'))return route.fulfill({json:{authenticated:true,development_superadmin:true,has_all_permissions:true}})
 if(u.pathname==='/api/finance-dashboard/')return route.fulfill({json:{period,metrics:{},due_items:[],monthly_cash:[],categories:[]}})
 if(u.pathname==='/api/actual-rmb-cash/') {if(u.searchParams.has('export')){count++;if(count===1)return route.fulfill({status:400,body:'failure'});await gate;return route.fulfill({contentType:'text/csv',body:'\ufeff实际资金,42'})}return route.fulfill({json:{basis:'bank_cash_confirmed_v1',period,totals:{inflow:'0',outflow:'0',net:'0',count:0},monthly:[],by_kind:[],events:[]}})} return route.fulfill({json:[]})})
 await page.goto('/finance?date_from=2026-10-01&date_to=2026-10-19');const button=page.getByRole('button',{name:'导出实际资金 CSV'});await expect(button).toBeEnabled();await button.click();await expect(page.getByRole('alert')).toBeVisible();await expect(button).toBeEnabled();await button.click();await expect(page.getByRole('button',{name:'导出中…'})).toBeDisabled();const downloading=page.waitForEvent('download');release();expect((await downloading).suggestedFilename()).toContain('2026-10-01-2026-10-19');expect(count).toBe(2);await expect(button).toBeEnabled()
})
