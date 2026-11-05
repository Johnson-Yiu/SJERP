# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: finance-csv-stability.spec.js >> actual cash export failure can retry and blocks duplicate pending requests
- Location: browser-tests\finance-csv-stability.spec.js:23:1

# Error details

```
Error: expect(locator).toBeDisabled() failed

Locator: getByRole('button', { name: '导出中…' })
Expected: disabled
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeDisabled" getByRole('button', { name: '导出中…' }) with timeout 5000ms
  - waiting for getByRole('button', { name: '导出中…' })

```

```yaml
- complementary:
  - text: S
  - strong: 森爵照明管理系统
  - text: 客户 · 销售 · 产品
  - navigation:
    - text: 经营
    - link "经营概览":
      - /url: /
    - link "报表中心":
      - /url: /reports
    - link "历史订单分析":
      - /url: /historical-orders
    - text: 客户
    - link "客户管理":
      - /url: /customers
    - link "联系人":
      - /url: /contacts
    - link "跟进记录":
      - /url: /follow-ups
    - text: 销售
    - link "报价管理":
      - /url: /quotes
    - link "订单管理":
      - /url: /orders
    - text: 采购与库存
    - link "供应商管理":
      - /url: /suppliers
    - link "采购管理":
      - /url: /purchase-orders
    - link "库存":
      - /url: /inventory
    - link "库存流水":
      - /url: /inventory-movements
    - text: 产品资料
    - link "产品管理":
      - /url: /products
    - link "SKU 管理":
      - /url: /skus
    - link "产品分类":
      - /url: /categories
    - link "产品参数":
      - /url: /product-parameters
    - link "包装管理":
      - /url: /sku-packaging
    - link "交易单位":
      - /url: /sku-trade-units
    - link "产品证书":
      - /url: /product-certificates
    - link "HS 编码维护":
      - /url: /hs-codes
    - text: 财务与工具
    - link "财务概览":
      - /url: /finance
    - link "应收计划":
      - /url: /receivables
    - link "应付计划":
      - /url: /payables
    - link "财务流水":
      - /url: /transactions
    - link "人民币资金":
      - /url: /rmb-cash-events
    - link "账户资金":
      - /url: /finance-ledger
    - link "数据导入":
      - /url: /import
    - link "历史资料承接":
      - /url: /history-takeover
    - text: 组织与系统
    - link "组织与权限":
      - /url: /organization
  - text: —
  - strong: 开发身份：
  - text: · 全部功能与数据权限
- main:
  - text: Operating finance
  - heading "财务概览" [level=1]
  - text: 11月5日周四 —
  - paragraph: 合同、应收应付与两种资金口径分开列示。合同按订单日期，账面收支按流水发生日期，银行实际资金按银行实际日期；当前待结与未核销是当前余额。
  - button "刷新数据"
  - form "概览日期范围":
    - text: 开始日期
    - textbox "开始日期": 2026-10-01
    - text: 结束日期
    - textbox "结束日期": 2026-10-19
    - button "查询"
    - button "本月至今"
    - button "导出 CSV"
  - paragraph: 合同销售额按订单日期，账面收支按流水发生日期。待收、待付按合同汇率折算，未核销预收预付按原流水汇率折算，均为当前参考值。银行实际人民币资金按银行实际日期统计；当前待结与未核销不受所选期间限制。预计订单利润 = 合同销售额 − 采购归属成本 − 订单费用，仅作经营估算。
  - paragraph: 账面人民币折算参考：已确认流水按既有人民币金额及流水汇率汇总，包含原币为CNY的既有流水；不代表银行实际到账、已完成结汇或银行账户余额。流水发生日期不等同于银行到账日。
  - heading "所选期间" [level=3]
  - paragraph: 2026-10-01 至 2026-10-19
  - article:
    - text: 合同销售额
    - strong: ¥0.00
    - button "查看构成明细"
  - article:
    - text: 预计订单利润
    - strong: ¥0.00
    - button "查看构成明细"
  - article:
    - text: 订单采购归属成本
    - strong: ¥0.00
    - button "查看构成明细"
  - article:
    - text: 订单费用
    - strong: ¥0.00
    - button "查看构成明细"
  - article:
    - text: 账面收入（折算参考）
    - strong: ¥0.00
    - button "查看构成明细"
  - article:
    - text: 账面支出（折算参考）
    - strong: ¥0.00
    - button "查看构成明细"
  - article:
    - text: 账面净收支（折算参考）
    - strong: ¥0.00
    - button "查看构成明细"
  - heading "当前待结与未核销（余额）" [level=3]
  - paragraph: 截至当前的待结与未核销金额，不受所选期间筛选限制
  - article:
    - text: 待收笔数
    - strong: 0 笔
    - button "查看构成明细"
  - article:
    - text: 待收款（人民币折算参考）
    - strong: ¥0.00
    - button "查看构成明细"
  - article:
    - text: 待付款笔数
    - strong: 0 笔
    - button "查看构成明细"
  - article:
    - text: 待付款（人民币折算参考）
    - strong: ¥0.00
    - button "查看构成明细"
  - article:
    - text: 未核销预收款（人民币折算参考）
    - strong: ¥0.00
    - button "查看构成明细"
  - article:
    - text: 未核销预付款（人民币折算参考）
    - strong: ¥0.00
    - button "查看构成明细"
  - region "银行实际人民币资金":
    - heading "银行实际人民币资金" [level=3]
    - paragraph: 统计已登记、已核实的人民币实际变动，银行与现金分开列示；不代表公司全部银行余额或现金余额。
    - button "查看构成明细"
    - button "导出实际资金 CSV"
    - alert:
      - text: 请求未能通过校验，请检查填写内容。
      - button "重新加载"
  - heading "月度账面收支（人民币折算参考）" [level=3]
  - paragraph: 所选期间暂无已确认账面收支记录。
  - heading "账面收支分类（人民币折算参考）" [level=3]
  - paragraph: 所选期间暂无账面收支分类记录。
  - navigation "财务模块快捷入口":
    - link "查看应收计划":
      - /url: /receivables
    - link "查看应付计划":
      - /url: /payables
    - link "查看财务流水":
      - /url: /transactions
    - link "人民币资金记录":
      - /url: /rmb-cash-events
  - heading "到期与逾期计划" [level=3]
  - paragraph: 暂无到期或逾期计划。
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
  17 |  await button.click(); await expect(page.getByRole('alert').first()).toBeVisible(); await expect(button).toBeEnabled(); await button.click(); await expect(page.getByRole('button',{name:'正在导出…'})).toBeDisabled()
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
> 29 |  await page.goto('/finance?date_from=2026-10-01&date_to=2026-10-19');const button=page.getByRole('button',{name:'导出实际资金 CSV'});await expect(button).toBeEnabled();await button.click();await expect(page.getByRole('alert')).toBeVisible();await expect(button).toBeEnabled();await button.click();await expect(page.getByRole('button',{name:'导出中…'})).toBeDisabled();const downloading=page.waitForEvent('download');release();expect((await downloading).suggestedFilename()).toContain('2026-10-01-2026-10-19');expect(count).toBe(2);await expect(button).toBeEnabled()
     |                                                                                                                                                                                                                                                                                                                                                         ^ Error: expect(locator).toBeDisabled() failed
  30 | })
  31 | 
```