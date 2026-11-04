# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: finance-closeout.spec.js >> real account ledger at 1440px
- Location: browser-tests\finance-closeout.spec.js:11:34

# Error details

```
Error: download.saveAs: canceled
```

# Page snapshot

```yaml
- generic [ref=f1e3]:
  - complementary [ref=f1e4]:
    - generic [ref=f1e5]:
      - generic [ref=f1e6]: S
      - generic [ref=f1e7]:
        - strong [ref=f1e8]: 森爵照明管理系统
        - text: 客户 · 销售 · 产品
    - navigation [ref=f1e9]:
      - generic [ref=f1e10]: 经营
      - link "经营概览" [ref=f1e11] [cursor=pointer]:
        - /url: /
      - link "报表中心" [ref=f1e18] [cursor=pointer]:
        - /url: /reports
      - link "历史订单分析" [ref=f1e25] [cursor=pointer]:
        - /url: /historical-orders
      - generic [ref=f1e31]: 客户
      - link "客户管理" [ref=f1e32] [cursor=pointer]:
        - /url: /customers
      - link "联系人" [ref=f1e39] [cursor=pointer]:
        - /url: /contacts
      - link "跟进记录" [ref=f1e45] [cursor=pointer]:
        - /url: /follow-ups
      - generic [ref=f1e49]: 销售
      - link "报价管理" [ref=f1e50] [cursor=pointer]:
        - /url: /quotes
      - link "订单管理" [ref=f1e55] [cursor=pointer]:
        - /url: /orders
      - generic [ref=f1e61]: 采购与库存
      - link "供应商管理" [ref=f1e62] [cursor=pointer]:
        - /url: /suppliers
      - link "采购管理" [ref=f1e69] [cursor=pointer]:
        - /url: /purchase-orders
      - link "库存" [ref=f1e75] [cursor=pointer]:
        - /url: /inventory
      - link "库存流水" [ref=f1e80] [cursor=pointer]:
        - /url: /inventory-movements
      - generic [ref=f1e85]: 产品资料
      - link "产品管理" [ref=f1e86] [cursor=pointer]:
        - /url: /products
      - link "SKU 管理" [ref=f1e92] [cursor=pointer]:
        - /url: /skus
      - link "产品分类" [ref=f1e104] [cursor=pointer]:
        - /url: /categories
      - link "产品参数" [ref=f1e110] [cursor=pointer]:
        - /url: /product-parameters
      - link "包装管理" [ref=f1e113] [cursor=pointer]:
        - /url: /sku-packaging
      - link "交易单位" [ref=f1e119] [cursor=pointer]:
        - /url: /sku-trade-units
      - link "产品证书" [ref=f1e131] [cursor=pointer]:
        - /url: /product-certificates
      - link "HS 编码维护" [ref=f1e136] [cursor=pointer]:
        - /url: /hs-codes
      - generic [ref=f1e139]: 财务与工具
      - link "财务概览" [ref=f1e140] [cursor=pointer]:
        - /url: /finance
      - link "应收计划" [ref=f1e146] [cursor=pointer]:
        - /url: /receivables
      - link "应付计划" [ref=f1e152] [cursor=pointer]:
        - /url: /payables
      - link "财务流水" [ref=f1e158] [cursor=pointer]:
        - /url: /transactions
      - link "人民币资金" [ref=f1e164] [cursor=pointer]:
        - /url: /rmb-cash-events
      - link "账户资金" [ref=f1e170] [cursor=pointer]:
        - /url: /finance-ledger
      - link "数据导入" [ref=f1e176] [cursor=pointer]:
        - /url: /import
      - link "历史资料承接" [ref=f1e181] [cursor=pointer]:
        - /url: /history-takeover
      - generic [ref=f1e187]: 组织与系统
      - link "组织与权限" [ref=f1e188] [cursor=pointer]:
        - /url: /organization
    - generic [ref=f1e193]:
      - generic [ref=f1e194]: J
      - generic [ref=f1e196]:
        - strong [ref=f1e197]: 开发身份：Johnson
        - generic [ref=f1e198]: 超级管理员 · 全部功能与数据权限
  - main [ref=f1e199]:
    - generic [ref=f1e200]:
      - generic [ref=f1e201]:
        - text: Account cash
        - heading "账户资金" [level=1] [ref=f1e202]
      - generic [ref=f1e203]:
        - generic [ref=f1e204]: 11月5日周四
        - generic "Johnson" [ref=f1e205]: J
    - generic [ref=f1e207]:
      - generic [ref=f1e208]:
        - generic [ref=f1e209]:
          - heading "账户资金" [level=1] [ref=f1e210]
          - paragraph [ref=f1e211]: 按真实账户核对人民币变动、凭证和处理记录。
        - button "刷新" [ref=f1e212] [cursor=pointer]
      - navigation "资金功能" [ref=f1e213]:
        - button "资金事实" [pressed] [ref=f1e214] [cursor=pointer]
        - button "登记与复核" [ref=f1e215] [cursor=pointer]
        - button "账户与映射" [ref=f1e216] [cursor=pointer]
        - button "账户核对" [ref=f1e217] [cursor=pointer]
        - button "转账与分类" [ref=f1e218] [cursor=pointer]
      - generic [ref=f1e219]:
        - generic [ref=f1e220]:
          - generic [ref=f1e221]:
            - text: 开始日期
            - textbox "开始日期" [ref=f1e222]: 2026-01-01
          - generic [ref=f1e223]:
            - text: 结束日期
            - textbox "结束日期" [ref=f1e224]: 2026-01-31
          - button "查询" [ref=f1e225] [cursor=pointer]
          - button "导出 CSV" [ref=f1e226] [cursor=pointer]
        - generic [ref=f1e227]:
          - generic [ref=f1e228]: 公司流入 ¥123.45
          - generic [ref=f1e229]: 公司流出 ¥0
          - generic [ref=f1e230]: 净变动 ¥123.45
        - paragraph [ref=f1e231]: 本页汇总新承接的账户事实。启用余额不计收入，已核实内部本金不计公司毛流量；账户明细保留两端变动。已有银行事实见人民币资金页，合并统计见财务概览。
        - generic [ref=f1e232]:
          - article [ref=f1e233]:
            - strong [ref=f1e234]: 合成核对银行-1440
            - paragraph [ref=f1e235]: 银行 · 自有
            - paragraph [ref=f1e236]: 余额：未设置启用基准
          - article [ref=f1e237]:
            - strong [ref=f1e238]: 合成核对现金-1440
            - paragraph [ref=f1e239]: 现金 · 自有
            - paragraph [ref=f1e240]: 余额：未设置启用基准
          - article [ref=f1e241]:
            - strong [ref=f1e242]: 合成核对银行-390
            - paragraph [ref=f1e243]: 银行 · 自有
            - paragraph [ref=f1e244]: 余额：未设置启用基准
          - article [ref=f1e245]:
            - strong [ref=f1e246]: 合成核对现金-390
            - paragraph [ref=f1e247]: 现金 · 自有
            - paragraph [ref=f1e248]: 余额：未设置启用基准
          - article [ref=f1e249]:
            - strong [ref=f1e250]: 合成验收银行-1440-1793818263046
            - paragraph [ref=f1e251]: 银行 · 自有
            - paragraph [ref=f1e252]: 余额：未设置启用基准
        - article [ref=f1e254]:
          - strong [ref=f1e255]: "#17 · 合成验收银行-1440-1793818263046 · +¥123.45"
          - paragraph [ref=f1e256]: 2026-01-02 · 实际收支 · 性质待分类
          - paragraph [ref=f1e257]: 计入公司毛流量 · 来源 SYNTH-CHROME / SYNTH-ROW-1440-1793818263046
          - link "下载私有凭证" [ref=f1e258] [cursor=pointer]:
            - /url: /api/finance-ledger/voucher-download/?id=7
          - group [ref=f1e259]:
            - generic "凭证摘要与历史分类" [ref=f1e260]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import fs from 'node:fs/promises'
  3  | import path from 'node:path'
  4  | import { syntheticVoucherPdf } from './helpers/bank-voucher.js'
  5  | 
  6  | test.use({ channel: 'chrome' })
  7  | const root = process.env.FINANCE_CLOSEOUT_EVIDENCE || (process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
  8  |   ? path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'browser', 'finance-closeout')
  9  |   : '../docs/uat-evidence/finance-closeout-batch-20261104/browser')
  10 | 
  11 | for (const width of [1440, 390]) test(`real account ledger at ${width}px`, async ({ page }) => {
  12 |   await fs.mkdir(root, { recursive: true })
  13 |   const records = [], errors = []
  14 |   page.on('pageerror', error => errors.push(error.message))
  15 |   page.on('response', async response => {
  16 |     if (!response.url().includes('/api/finance-ledger/')) return
  17 |     try { records.push({ url: new URL(response.url()).pathname, method: response.request().method(), status: response.status(), body: await response.json() }) } catch { /* Actual file downloads are saved separately. */ }
  18 |   })
  19 |   const suffix = `${width}-${Date.now()}`
  20 |   await page.setViewportSize({ width, height: 1050 })
  21 |   await page.goto('/finance-ledger')
  22 |   await expect(page.locator('.ledger-page').getByRole('heading', { name: '账户资金', exact: true })).toBeVisible()
  23 |   await page.getByRole('button', { name: '账户与映射', exact: true }).click()
  24 |   await page.getByLabel('受控标识', { exact: true }).fill(`SYNTH-${suffix}`)
  25 |   await page.getByLabel('显示名称', { exact: true }).fill(`合成验收银行-${suffix}`)
  26 |   await page.getByLabel('归属', { exact: true }).selectOption('own')
  27 |   await page.getByLabel('归属核实依据', { exact: true }).fill('合成银行开户核实，非真实账户')
  28 |   const accountResponse = page.waitForResponse(r => r.url().endsWith('/api/finance-ledger/accounts/') && r.request().method() === 'POST')
  29 |   await page.getByRole('button', { name: '保存账户', exact: true }).click()
  30 |   const accountHttp = await accountResponse
  31 |   expect(accountHttp.status()).toBe(201)
  32 |   const account = await accountHttp.json()
  33 |   await expect(page.getByRole('status')).toHaveText('账户已建立。')
  34 |   await page.getByRole('button', { name: '登记与复核', exact: true }).click()
  35 |   await page.getByLabel('凭证文件（PDF / PNG / JPEG，最多10MB）').setInputFiles({ name: `synthetic-${suffix}.pdf`, mimeType: 'application/pdf', buffer: syntheticVoucherPdf() })
  36 |   const uploadResponse = page.waitForResponse(r => r.url().endsWith('/api/finance-ledger/vouchers/'))
  37 |   await page.getByRole('button', { name: '上传凭证', exact: true }).click()
  38 |   expect((await uploadResponse).status()).toBe(201)
  39 |   await expect(page.getByRole('status')).toContainText('摘要由系统读取文件计算')
  40 |   await page.getByLabel('自有账户', { exact: true }).selectOption(String(account.id))
  41 |   await page.getByLabel('实际日期', { exact: true }).fill('2026-01-02')
  42 |   await page.getByLabel('人民币金额', { exact: true }).fill('123.45')
  43 |   await page.getByLabel('真实性', { exact: true }).selectOption('verified')
  44 |   await page.getByLabel('来源系统', { exact: true }).fill('SYNTH-CHROME')
  45 |   await page.getByLabel('来源编号', { exact: true }).fill(`SYNTH-ROW-${suffix}`)
  46 |   await page.getByLabel('原因及凭证依据', { exact: true }).fill('合成银行凭证已核实，性质暂未分类')
  47 |   await page.getByRole('button', { name: '只读预检', exact: true }).click()
  48 |   await expect(page.getByRole('status')).toContainText('尚未写入')
  49 |   const requestKey = await page.getByLabel('请求标识', { exact: true }).inputValue()
  50 |   const submitResponse = page.waitForResponse(r => r.url().endsWith('/api/finance-ledger/instructions/'))
  51 |   await page.getByRole('button', { name: '保存指令', exact: true }).click()
  52 |   const submitted = await submitResponse
  53 |   expect(submitted.status()).toBe(201)
  54 |   const instruction = await submitted.json()
  55 |   expect(instruction.payload.request_key).toBe(requestKey)
  56 |   await page.reload()
  57 |   await page.getByRole('button', { name: '登记与复核', exact: true }).click()
  58 |   await expect(page.getByLabel('请求标识', { exact: true })).toHaveValue(requestKey)
  59 |   await expect(page.getByText(`已恢复待核查请求 ${requestKey}`, { exact: false })).toBeVisible()
  60 |   const card = page.locator('article').filter({ hasText: `指令 #${instruction.id} ·` })
  61 |   await card.getByRole('button', { name: '另一人复核', exact: true }).click()
  62 |   await expect(page.getByRole('alert')).toContainText('两名真实认证人员')
  63 |   await page.getByLabel('已核对实际日期、人民币金额及文件凭证', { exact: true }).check()
  64 |   await card.getByRole('button', { name: '确认实际记账', exact: true }).click()
  65 |   await expect(card).toContainText('已记账')
  66 |   await page.getByRole('button', { name: '资金事实', exact: true }).click()
  67 |   await page.getByLabel('开始日期', { exact: true }).fill('2026-01-01')
  68 |   await page.getByLabel('结束日期', { exact: true }).fill('2026-01-31')
  69 |   await page.getByRole('button', { name: '查询', exact: true }).click()
  70 |   const fact = page.locator('article').filter({ hasText: `SYNTH-ROW-${suffix}` })
  71 |   await expect(fact).toContainText('性质待分类')
  72 |   await expect(fact).toContainText('123.45')
  73 |   const downloaded = page.waitForEvent('download')
  74 |   await page.getByRole('button', { name: '导出 CSV', exact: true }).click()
> 75 |   await (await downloaded).saveAs(path.join(root, `facts-${width}.csv`))
     |                            ^ Error: download.saveAs: canceled
  76 |   const csv = await fs.readFile(path.join(root, `facts-${width}.csv`), 'utf8')
  77 |   expect(csv).toContain(`SYNTH-ROW-${suffix}`)
  78 |   expect(csv).toContain('123.45')
  79 |   const dimensions = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }))
  80 |   expect(dimensions.document).toBeLessThanOrEqual(width)
  81 |   await page.evaluate(() => window.scrollTo(0, 0))
  82 |   await page.screenshot({ path: path.join(root, `account-facts-${width}.png`), fullPage: true })
  83 |   const factId = (await fact.getAttribute('id')).replace('fact-', '')
  84 |   await page.goto(`/finance-ledger?fact=${factId}`)
  85 |   await expect(page.getByLabel('开始日期', { exact: true })).toHaveValue('2026-01-02')
  86 |   await expect(page.locator(`#fact-${factId}`)).toBeVisible()
  87 |   expect(errors).toEqual([])
  88 |   await fs.writeFile(path.join(root, `http-${width}.json`), JSON.stringify({ records, dimensions, errors }, null, 2))
  89 | })
  90 | 
```