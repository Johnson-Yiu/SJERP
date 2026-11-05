# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: finance-csv-stability.spec.js >> CSV retry and changing period 1440
- Location: browser-tests\finance-csv-stability.spec.js:8:32

# Error details

```
Error: expect(locator).toBeEnabled() failed

Locator:  getByRole('button', { name: '导出 CSV', exact: true })
Expected: enabled
Received: disabled
Timeout:  5000ms

Call log:
  - Expect "toBeEnabled" getByRole('button', { name: '导出 CSV', exact: true }) with timeout 5000ms
  - waiting for getByRole('button', { name: '导出 CSV', exact: true })
    14 × locator resolved to <button disabled type="button" class="secondary" data-v-3935f5ee="">导出 CSV</button>
       - unexpected value "disabled"

```

```yaml
- button "导出 CSV" [disabled]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import fs from 'node:fs'
  3  | import path from 'node:path'
  4  | const dir=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
  5  |   ? path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'finance-csv-stability')
  6  |   : path.resolve('../docs/uat-evidence/export-stability-closeout-20261105/finance')
  7  | fs.mkdirSync(dir,{recursive:true})
  8  | for(const width of [1440,390]) test(`CSV retry and changing period ${width}`,async({page})=>{
  9  |  await page.setViewportSize({width,height:900}); let count=0, release; const gate=new Promise(r=>release=r)
  10 |  await page.route('**/api/**',async route=>{const u=new URL(route.request().url()), from=u.searchParams.get('date_from'),to=u.searchParams.get('date_to');
  11 |  if(u.pathname.includes('current-operator')) return route.fulfill({json:{authenticated:true,development_superadmin:true,has_all_permissions:true}})
  12 |  if(['/api/finance-dashboard/','/api/actual-rmb-cash/'].includes(u.pathname)) {
  13 |  if(u.searchParams.has('export')) {count++; if(count===1)return route.fulfill({status:400,body:'failed'}); if(count===2)await gate; return route.fulfill({contentType:'text/csv',body:'\ufeff期间,金额\r\n'+from+',42\r\n'})}
  14 |  if(u.pathname.includes('dashboard'))return route.fulfill({json:{period:{date_from:from,date_to:to},metrics:{},due_items:[],monthly_cash:[],categories:[]}})
  15 |  return route.fulfill({json:{basis:'bank_cash_confirmed_v1',period:{date_from:from,date_to:to},totals:{inflow:'0',outflow:'0',net:'0',count:0},monthly:[],by_kind:[],events:[]}})} return route.fulfill({json:[]})})
  16 |  await page.goto('/finance?date_from=2026-10-01&date_to=2026-10-19'); const button=page.getByRole('button',{name:'导出 CSV',exact:true}); await expect(button).toBeEnabled(); await page.screenshot({path:path.join(dir,`finance-${width}.png`),fullPage:true})
> 17 |  await button.click(); await expect(page.getByRole('alert').first()).toBeVisible(); await expect(button).toBeEnabled(); await button.click(); await expect(page.getByRole('button',{name:'正在导出…'})).toBeDisabled()
     |                                                                                                          ^ Error: expect(locator).toBeEnabled() failed
  18 |  await page.getByLabel('开始日期').fill('2026-09-01'); await page.getByLabel('结束日期').fill('2026-09-30'); await page.getByRole('button',{name:'查询',exact:true}).click(); await expect(page).toHaveURL(/2026-09-30/)
  19 |  const downloading=page.waitForEvent('download'); release(); const download=await downloading; expect(download.suggestedFilename()).toContain('2026-10-01-2026-10-19'); const bytes=fs.readFileSync(await download.path()); expect(bytes.subarray(0,3)).toEqual(Buffer.from([239,187,191])); expect(bytes.toString()).toContain('2026-10-01,42')
  20 |  const again=page.waitForEvent('download'); await button.click(); expect((await again).suggestedFilename()).toContain('2026-09-01-2026-09-30'); await page.goto('/transactions'); await page.goto('/finance?date_from=2026-09-01&date_to=2026-09-30'); await expect(button).toBeEnabled()
  21 | })
  22 | 
  23 | test('actual cash export failure can retry and blocks duplicate pending requests',async({page})=>{
  24 |  let count=0, release; const gate=new Promise(r=>release=r)
  25 |  await page.route('**/api/**',async route=>{const u=new URL(route.request().url()),period={date_from:u.searchParams.get('date_from'),date_to:u.searchParams.get('date_to')};
  26 |  if(u.pathname.includes('current-operator'))return route.fulfill({json:{authenticated:true,development_superadmin:true,has_all_permissions:true}})
  27 |  if(u.pathname==='/api/finance-dashboard/')return route.fulfill({json:{period,metrics:{},due_items:[],monthly_cash:[],categories:[]}})
  28 |  if(u.pathname==='/api/actual-rmb-cash/') {if(u.searchParams.has('export')){count++;if(count===1)return route.fulfill({status:400,body:'failure'});await gate;return route.fulfill({contentType:'text/csv',body:'\ufeff实际资金,42'})}return route.fulfill({json:{basis:'bank_cash_confirmed_v1',period,totals:{inflow:'0',outflow:'0',net:'0',count:0},monthly:[],by_kind:[],events:[]}})} return route.fulfill({json:[]})})
  29 |  await page.goto('/finance?date_from=2026-10-01&date_to=2026-10-19');const button=page.getByRole('button',{name:'导出实际资金 CSV'});await expect(button).toBeEnabled();await button.click();await expect(page.getByRole('alert')).toBeVisible();await expect(button).toBeEnabled();await button.click();await expect(page.getByRole('button',{name:'导出中…'})).toBeDisabled();const downloading=page.waitForEvent('download');release();expect((await downloading).suggestedFilename()).toContain('2026-10-01-2026-10-19');expect(count).toBe(2);await expect(button).toBeEnabled()
  30 | })
  31 | 
```