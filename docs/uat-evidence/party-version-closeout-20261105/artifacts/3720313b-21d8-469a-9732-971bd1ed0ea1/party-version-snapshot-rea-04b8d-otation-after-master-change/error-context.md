# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: party-version-snapshot-real.spec.js >> saved buyer country and PI use the saved quotation after master change
- Location: browser-tests\party-version-snapshot-real.spec.js:8:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.waitForResponse: Test timeout of 30000ms exceeded.
```

# Page snapshot

```yaml
- generic [ref=f2e3]:
  - complementary [ref=f2e4]:
    - generic [ref=f2e5]:
      - generic [ref=f2e6]: S
      - generic [ref=f2e7]:
        - strong [ref=f2e8]: 森爵照明管理系统
        - text: 客户 · 销售 · 产品
    - navigation [ref=f2e9]:
      - generic [ref=f2e10]: 经营
      - link "经营概览" [ref=f2e11] [cursor=pointer]:
        - /url: /
      - link "报表中心" [ref=f2e18] [cursor=pointer]:
        - /url: /reports
      - link "历史订单分析" [ref=f2e25] [cursor=pointer]:
        - /url: /historical-orders
      - generic [ref=f2e31]: 客户
      - link "客户管理" [ref=f2e32] [cursor=pointer]:
        - /url: /customers
      - link "联系人" [ref=f2e39] [cursor=pointer]:
        - /url: /contacts
      - link "跟进记录" [ref=f2e45] [cursor=pointer]:
        - /url: /follow-ups
      - generic [ref=f2e49]: 销售
      - link "报价管理" [ref=f2e50] [cursor=pointer]:
        - /url: /quotes
      - link "订单管理" [ref=f2e55] [cursor=pointer]:
        - /url: /orders
      - generic [ref=f2e61]: 采购与库存
      - link "供应商管理" [ref=f2e62] [cursor=pointer]:
        - /url: /suppliers
      - link "采购管理" [ref=f2e69] [cursor=pointer]:
        - /url: /purchase-orders
      - link "库存" [ref=f2e75] [cursor=pointer]:
        - /url: /inventory
      - link "库存流水" [ref=f2e80] [cursor=pointer]:
        - /url: /inventory-movements
      - generic [ref=f2e85]: 产品资料
      - link "产品管理" [ref=f2e86] [cursor=pointer]:
        - /url: /products
      - link "SKU 管理" [ref=f2e92] [cursor=pointer]:
        - /url: /skus
      - link "产品分类" [ref=f2e104] [cursor=pointer]:
        - /url: /categories
      - link "产品参数" [ref=f2e110] [cursor=pointer]:
        - /url: /product-parameters
      - link "包装管理" [ref=f2e113] [cursor=pointer]:
        - /url: /sku-packaging
      - link "交易单位" [ref=f2e119] [cursor=pointer]:
        - /url: /sku-trade-units
      - link "产品证书" [ref=f2e131] [cursor=pointer]:
        - /url: /product-certificates
      - link "HS 编码维护" [ref=f2e136] [cursor=pointer]:
        - /url: /hs-codes
      - generic [ref=f2e139]: 财务与工具
      - link "财务概览" [ref=f2e140] [cursor=pointer]:
        - /url: /finance
      - link "应收计划" [ref=f2e146] [cursor=pointer]:
        - /url: /receivables
      - link "应付计划" [ref=f2e152] [cursor=pointer]:
        - /url: /payables
      - link "财务流水" [ref=f2e158] [cursor=pointer]:
        - /url: /transactions
      - link "人民币资金" [ref=f2e164] [cursor=pointer]:
        - /url: /rmb-cash-events
      - link "账户资金" [ref=f2e170] [cursor=pointer]:
        - /url: /finance-ledger
      - link "数据导入" [ref=f2e176] [cursor=pointer]:
        - /url: /import
      - link "历史资料承接" [ref=f2e181] [cursor=pointer]:
        - /url: /history-takeover
      - generic [ref=f2e187]: 组织与系统
      - link "组织与权限" [ref=f2e188] [cursor=pointer]:
        - /url: /organization
    - generic [ref=f2e193]:
      - generic [ref=f2e194]: J
      - generic [ref=f2e196]:
        - strong [ref=f2e197]: 开发身份：Johnson
        - generic [ref=f2e198]: 超级管理员 · 全部功能与数据权限
  - main [ref=f2e199]:
    - generic [ref=f2e200]:
      - button [ref=f2e201] [cursor=pointer]
      - generic [ref=f2e203]:
        - text: Quotation desk
        - heading "报价管理" [level=1] [ref=f2e204]
      - generic "Johnson" [ref=f2e206]: J
    - generic [ref=f2e208]:
      - generic [ref=f2e209]:
        - paragraph [ref=f2e210]: 管理报价、修订版及转单进度。
        - button "新建报价" [ref=f2e211] [cursor=pointer]
      - region "报价汇总" [ref=f2e213]:
        - article [ref=f2e214]:
          - generic [ref=f2e215]: 报价主单
          - strong [ref=f2e216]: "1"
          - generic [ref=f2e220]: 主单数量
        - article [ref=f2e221]:
          - generic [ref=f2e222]: 报价修订版
          - strong [ref=f2e223]: "2"
          - generic [ref=f2e228]: 含全部版本
        - article [ref=f2e229]:
          - generic [ref=f2e230]: 跟进中
          - strong [ref=f2e231]: "2"
          - generic [ref=f2e236]: 草稿或已发送
        - article [ref=f2e237]:
          - generic [ref=f2e238]: 客户已接受
          - strong [ref=f2e239]: "0"
          - generic [ref=f2e244]: 已接受报价
      - generic [ref=f2e245]:
        - textbox "搜索报价单号或客户" [ref=f2e250]
        - combobox "按报价状态筛选" [ref=f2e251]:
          - option "全部状态" [selected]
          - option "草稿"
          - option "已发送"
          - option "已接受"
          - option "已拒绝"
          - option "已过期"
        - combobox "按客户筛选" [ref=f2e252]:
          - option "全部客户" [selected]
          - option "Synthetic Freeze Buyer AE84D062"
        - combobox "报价排序" [ref=f2e253]:
          - option "最近更新时间" [selected]
          - option "最早更新时间"
          - option "报价日期（新到旧）"
          - option "报价日期（旧到新）"
        - button "重置" [ref=f2e254] [cursor=pointer]
      - table [ref=f2e260]:
        - rowgroup [ref=f2e261]:
          - row [ref=f2e262]:
            - columnheader "报价单 / 层级" [ref=f2e263]
            - columnheader "客户" [ref=f2e264]
            - columnheader "更新时间" [ref=f2e265]
            - columnheader "状态" [ref=f2e266]
            - columnheader "明细" [ref=f2e267]
            - columnheader "金额" [ref=f2e268]
            - columnheader "操作" [ref=f2e269]
        - rowgroup [ref=f2e270]:
          - row [ref=f2e271] [cursor=pointer]:
            - cell "展开 SYNTH-AE84D062 的修订报价 SYNTH-AE84D062 原始报价" [ref=f2e272]:
              - generic [ref=f2e273]:
                - button "展开 SYNTH-AE84D062 的修订报价" [ref=f2e275]
                - generic [ref=f2e280]:
                  - strong [ref=f2e281]: SYNTH-AE84D062
                  - generic [ref=f2e282]: 原始报价
            - cell "Synthetic Freeze Buyer AE84D062" [ref=f2e283]
            - cell "2026/11/05 12:47" [ref=f2e284]
            - cell "草稿" [ref=f2e285]
            - cell "1 项" [ref=f2e287]
            - cell "USD 10.00" [ref=f2e288]
            - cell [ref=f2e289]:
              - generic [ref=f2e290]:
                - button "查看 SYNTH-AE84D062" [ref=f2e291]
                - button "创建修订版 SYNTH-AE84D062" [ref=f2e295]
                - button "导出 SYNTH-AE84D062" [ref=f2e299]
      - dialog "报价工作台" [ref=f2e304]:
        - generic [ref=f2e305]:
          - generic [ref=f2e307]:
            - button "关闭报价详情" [ref=f2e308] [cursor=pointer]
            - generic [ref=f2e312]: 报价工作台 · SYNTH-AE84D062
          - generic [ref=f2e313]:
            - generic [ref=f2e314]:
              - paragraph [ref=f2e315]: Synthetic Freeze Buyer AE84D062 · 原始报价
              - heading "SYNTH-AE84D062" [level=2] [ref=f2e316]
              - text: 原始报价：SYNTH-AE84D062
            - generic [ref=f2e317]: 草稿
          - generic "报价状态操作" [ref=f2e318]:
            - button "标记为已发送" [ref=f2e319] [cursor=pointer]
            - button "标记为客户已接受" [ref=f2e320] [cursor=pointer]
            - button "标记为客户已拒绝" [ref=f2e321] [cursor=pointer]
          - generic [ref=f2e322]:
            - button "创建修订版" [ref=f2e323] [cursor=pointer]
            - button "预览 PI" [ref=f2e327] [cursor=pointer]
            - button "导出 Excel" [ref=f2e331] [cursor=pointer]
            - button "创建销售订单" [ref=f2e335] [cursor=pointer]
        - main [ref=f2e340]:
          - navigation "报价详情分页" [ref=f2e341]:
            - button "概览" [ref=f2e342] [cursor=pointer]
            - button "报价明细 (1)" [ref=f2e343] [cursor=pointer]
            - button "版本谱系 (2)" [ref=f2e344] [cursor=pointer]
            - button "订单 (0)" [ref=f2e345] [cursor=pointer]
            - button "重要备注 (0)" [ref=f2e346] [cursor=pointer]
            - button "操作日志 (0)" [ref=f2e347] [cursor=pointer]
          - generic [ref=f2e348]:
            - generic [ref=f2e349]:
              - heading "报价概览" [level=3] [ref=f2e350]
              - generic [ref=f2e351]:
                - generic [ref=f2e352]:
                  - generic [ref=f2e353]: 报价总额
                  - strong [ref=f2e354]: USD 10.00
                - generic [ref=f2e355]:
                  - generic [ref=f2e356]: 有效期至
                  - strong [ref=f2e357]: —
                - generic [ref=f2e358]:
                  - generic [ref=f2e359]: 商品明细
                  - strong [ref=f2e360]: 1 项
            - generic [ref=f2e361]:
              - heading "基础信息" [level=3] [ref=f2e362]
              - generic [ref=f2e363]:
                - term [ref=f2e364]: 报价日期
                - definition [ref=f2e365]: 2026-11-03
                - term [ref=f2e366]: 币种 / 汇率
                - definition [ref=f2e367]: USD / 1
                - term [ref=f2e368]: 收件人
                - definition [ref=f2e369]: —
                - term [ref=f2e370]: 条款备注
                - definition [ref=f2e371]: —
            - generic [ref=f2e372]:
              - generic [ref=f2e373]:
                - generic [ref=f2e374]:
                  - heading "修订摘要" [level=3] [ref=f2e375]
                  - paragraph [ref=f2e380]: 共 2 个版本，当前查看 原始报价。
                - button "查看修订历史" [ref=f2e381] [cursor=pointer]
              - generic [ref=f2e382]:
                - article [ref=f2e383]:
                  - generic [ref=f2e384]:
                    - strong [ref=f2e385]: SYNTH-AE84D062
                    - generic [ref=f2e386]: 原始报价
                    - generic [ref=f2e387]: 2026/11/05 12:47
                    - generic [ref=f2e388]: 草稿
                  - generic [ref=f2e389]:
                    - text: USD 10.00
                    - generic [ref=f2e390]:
                      - button "预览 PI" [ref=f2e391] [cursor=pointer]
                      - button "查看详情" [disabled] [ref=f2e392] [cursor=pointer]
                - article [ref=f2e393]:
                  - generic [ref=f2e394]:
                    - strong [ref=f2e398]: SYNTH-AE84D062-1
                    - generic [ref=f2e399]: 修订版 1
                    - generic [ref=f2e400]: 2026/11/05 12:47
                    - generic [ref=f2e401]: 草稿
                    - emphasis [ref=f2e402]: 修订：Synthetic revision
                  - generic [ref=f2e403]:
                    - text: USD 10.00
                    - generic [ref=f2e404]:
                      - button "预览 PI" [ref=f2e405] [cursor=pointer]
                      - button "查看详情" [ref=f2e406] [cursor=pointer]
            - generic [ref=f2e407]:
              - heading "销售订单摘要" [level=3] [ref=f2e408]
              - paragraph [ref=f2e413]: 已生成 0 张销售订单。
              - button "查看关联销售订单" [ref=f2e414] [cursor=pointer]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import { spawnSync } from 'node:child_process'
  3  | import fs from 'node:fs'
  4  | import path from 'node:path'
  5  | 
  6  | test.use({ channel: 'chrome' })
  7  | 
  8  | test('saved buyer country and PI use the saved quotation after master change', async ({ page }) => {
  9  |   expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  10 |   const fixtureRoot = path.resolve('../docs/uat-evidence/r1-iss037-seller-template-freeze-20261103')
  11 |   const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(fixtureRoot, 'seed_browser.py')], {
  12 |     cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  13 |   })
  14 |   expect(seed.status, seed.stderr).toBe(0)
  15 |   const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  16 |   const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'party-version')
  17 |   fs.mkdirSync(evidence, { recursive: true })
  18 |   const before = await page.request.get(`/api/quotes/${fixture.id}/`)
  19 |   expect(before.status()).toBe(200)
  20 |   const quote = await before.json()
  21 |   expect(quote.buyer_country_snapshot).toBe('Germany')
  22 |   const changed = await page.request.patch(`/api/customers/${quote.customer}/`, { data: { country: 'France' } })
  23 |   expect(changed.status()).toBe(200)
  24 |   const after = await page.request.get(`/api/quotes/${fixture.id}/`)
  25 |   expect(after.status()).toBe(200)
  26 |   expect((await after.json()).buyer_country_snapshot).toBe('Germany')
  27 |   const revision = await page.request.post(`/api/quotes/${fixture.id}/revise/`, { data: { revision_summary: 'Synthetic revision' } })
  28 |   expect(revision.status()).toBe(201)
  29 |   expect((await revision.json()).buyer_country_snapshot).toBe('Germany')
  30 |   const exported = await page.request.get(`/api/quotes/${fixture.id}/export/`)
  31 |   expect(exported.status()).toBe(200)
  32 |   fs.writeFileSync(path.join(evidence, 'synthetic-saved-quote.xlsx'), await exported.body())
  33 |   const results = { before: before.status(), customerPatch: changed.status(), after: after.status(), revision: revision.status(), xlsx: exported.status(), savedCountry: 'Germany' }
  34 |   for (const width of [1440, 390]) {
  35 |     await page.setViewportSize({ width, height: 900 })
  36 |     await page.goto(`/quotes?detail=${fixture.id}`)
  37 |     const detail = page.getByRole('dialog', { name: '报价工作台' })
  38 |     await expect(detail).toBeVisible()
> 39 |     const response = page.waitForResponse(r => r.url().includes(`/quotes/${fixture.id}/pi-data/`))
     |                           ^ Error: page.waitForResponse: Test timeout of 30000ms exceeded.
  40 |     await detail.getByRole('button', { name: '预览 PI' }).first().click()
  41 |     const pi = await response
  42 |     expect(pi.status()).toBe(200)
  43 |     const data = await pi.json()
  44 |     await expect(page.frameLocator('iframe[title="已保存 PI"]').locator('body')).toContainText('Synthetic Seller')
  45 |     await expect(page.frameLocator('iframe[title="已保存 PI"]').locator('body')).toContainText(quote.buyer_company_name)
  46 |     await page.screenshot({ path: path.join(evidence, `saved-pi-${width}.png`) })
  47 |     results[`pi${width}`] = { status: pi.status(), buyer: data.buyer, seller: data.seller }
  48 |   }
  49 |   fs.writeFileSync(path.join(evidence, 'http.json'), JSON.stringify(results, null, 2))
  50 | })
  51 | 
```