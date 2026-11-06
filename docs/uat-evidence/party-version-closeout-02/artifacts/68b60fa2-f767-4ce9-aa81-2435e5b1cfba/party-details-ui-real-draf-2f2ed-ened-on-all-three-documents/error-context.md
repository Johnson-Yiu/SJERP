# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: party-details-ui-real.spec.js >> draft party details can be saved and reopened on all three documents
- Location: browser-tests\party-details-ui-real.spec.js:7:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.goto: Test timeout of 30000ms exceeded.
Call log:
  - navigating to "http://127.0.0.1:3337/quotes?detail=1", waiting until "load"

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
      - generic [ref=f2e194]: U
      - generic [ref=f2e196]:
        - strong [ref=f2e197]: 开发身份：ui-706064B8
        - generic [ref=f2e198]: 超级管理员 · 全部功能与数据权限
  - main [ref=f2e199]:
    - generic [ref=f2e200]:
      - generic [ref=f2e201]:
        - text: Quotation desk
        - heading "报价管理" [level=1] [ref=f2e202]
      - generic [ref=f2e203]:
        - generic [ref=f2e204]: 11月5日周四
        - generic "ui-706064B8" [ref=f2e205]: U
    - generic [ref=f2e207]:
      - generic [ref=f2e208]:
        - paragraph [ref=f2e209]: 管理报价、修订版及转单进度。
        - button "新建报价" [ref=f2e210] [cursor=pointer]
      - region "报价汇总" [ref=f2e212]:
        - article [ref=f2e213]:
          - generic [ref=f2e214]: 报价主单
          - strong [ref=f2e215]: "1"
          - generic [ref=f2e219]: 主单数量
        - article [ref=f2e220]:
          - generic [ref=f2e221]: 报价修订版
          - strong [ref=f2e222]: "1"
          - generic [ref=f2e227]: 含全部版本
        - article [ref=f2e228]:
          - generic [ref=f2e229]: 跟进中
          - strong [ref=f2e230]: "1"
          - generic [ref=f2e235]: 草稿或已发送
        - article [ref=f2e236]:
          - generic [ref=f2e237]: 客户已接受
          - strong [ref=f2e238]: "0"
          - generic [ref=f2e243]: 已接受报价
      - generic [ref=f2e244]:
        - textbox "搜索报价单号或客户" [ref=f2e249]
        - combobox "按报价状态筛选" [ref=f2e250]:
          - option "全部状态" [selected]
          - option "草稿"
          - option "已发送"
          - option "已接受"
          - option "已拒绝"
          - option "已过期"
        - combobox "按客户筛选" [ref=f2e251]:
          - option "全部客户" [selected]
          - option "Synthetic buyer"
        - combobox "报价排序" [ref=f2e252]:
          - option "最近更新时间" [selected]
          - option "最早更新时间"
          - option "报价日期（新到旧）"
          - option "报价日期（旧到新）"
        - button "重置" [ref=f2e253] [cursor=pointer]
      - table [ref=f2e259]:
        - rowgroup [ref=f2e260]:
          - row [ref=f2e261]:
            - columnheader "报价单 / 层级" [ref=f2e262]
            - columnheader "客户" [ref=f2e263]
            - columnheader "更新时间" [ref=f2e264]
            - columnheader "状态" [ref=f2e265]
            - columnheader "明细" [ref=f2e266]
            - columnheader "金额" [ref=f2e267]
            - columnheader "操作" [ref=f2e268]
        - rowgroup [ref=f2e269]:
          - row [ref=f2e270] [cursor=pointer]:
            - cell "UIQ706064B8 原始报价" [ref=f2e271]:
              - generic [ref=f2e277]:
                - strong [ref=f2e278]: UIQ706064B8
                - generic [ref=f2e279]: 原始报价
            - cell "Synthetic buyer" [ref=f2e280]
            - cell "2026/11/05 20:58" [ref=f2e281]
            - cell "草稿" [ref=f2e282]
            - cell "0 项" [ref=f2e284]
            - cell "USD 0.00" [ref=f2e285]
            - cell [ref=f2e286]:
              - generic [ref=f2e287]:
                - button "查看 UIQ706064B8" [ref=f2e288]
                - button "创建修订版 UIQ706064B8" [ref=f2e292]
                - button "导出 UIQ706064B8" [ref=f2e296]
      - dialog "报价工作台" [ref=f2e301]:
        - generic [ref=f2e302]:
          - generic [ref=f2e304]:
            - button "关闭报价详情" [ref=f2e305] [cursor=pointer]:
              - generic [ref=f2e309]: 关闭
            - generic [ref=f2e310]: 报价工作台 · UIQ706064B8
          - generic [ref=f2e311]:
            - generic [ref=f2e312]:
              - paragraph [ref=f2e313]: Synthetic buyer · 原始报价
              - heading "UIQ706064B8" [level=2] [ref=f2e314]
              - text: 原始报价：UIQ706064B8
            - generic [ref=f2e315]: 草稿
          - generic "报价状态操作" [ref=f2e316]:
            - button "标记为已发送" [ref=f2e317] [cursor=pointer]
            - button "标记为客户已接受" [ref=f2e318] [cursor=pointer]
            - button "标记为客户已拒绝" [ref=f2e319] [cursor=pointer]
          - generic [ref=f2e320]:
            - button "创建修订版" [ref=f2e321] [cursor=pointer]
            - button "预览 PI" [ref=f2e325] [cursor=pointer]
            - button "导出 Excel" [ref=f2e329] [cursor=pointer]
            - button "创建销售订单" [ref=f2e333] [cursor=pointer]
        - main [ref=f2e338]:
          - navigation "报价详情分页" [ref=f2e339]:
            - button "概览" [ref=f2e340] [cursor=pointer]
            - button "报价明细 (0)" [ref=f2e341] [cursor=pointer]
            - button "版本谱系 (1)" [ref=f2e342] [cursor=pointer]
            - button "订单 (0)" [ref=f2e343] [cursor=pointer]
            - button "主体更正" [ref=f2e344] [cursor=pointer]
            - button "重要备注 (0)" [ref=f2e345] [cursor=pointer]
            - button "操作日志 (0)" [ref=f2e346] [cursor=pointer]
          - generic [ref=f2e347]:
            - generic [ref=f2e348]:
              - heading "草稿双方资料" [level=3] [ref=f2e349]
              - paragraph [ref=f2e350]: 尚未记录；未知资料不会从当前主档补填。
              - generic [ref=f2e351]:
                - generic [ref=f2e352]:
                  - heading "买方" [level=4] [ref=f2e353]
                  - generic [ref=f2e355]:
                    - text: 买方名称
                    - textbox "买方名称" [ref=f2e356]:
                      - /placeholder: 未知
                  - generic [ref=f2e358]:
                    - text: 买方国家 / 地区
                    - textbox "买方国家 / 地区" [ref=f2e359]:
                      - /placeholder: 未知
                  - generic [ref=f2e361]:
                    - text: 买方地址
                    - textbox "买方地址" [ref=f2e362]:
                      - /placeholder: 未知
                  - generic [ref=f2e364]:
                    - text: 买方税号
                    - textbox "买方税号" [ref=f2e365]:
                      - /placeholder: 未知
                  - generic [ref=f2e367]:
                    - text: 买方联系人
                    - textbox "买方联系人" [ref=f2e368]:
                      - /placeholder: 未知
                  - generic [ref=f2e370]:
                    - text: 买方电话
                    - textbox "买方电话" [ref=f2e371]:
                      - /placeholder: 未知
                  - generic [ref=f2e373]:
                    - text: 买方邮箱
                    - textbox "买方邮箱" [ref=f2e374]:
                      - /placeholder: 未知
                  - generic [ref=f2e376]:
                    - text: 买方账单地址
                    - textbox "买方账单地址" [ref=f2e377]:
                      - /placeholder: 未知
                  - generic [ref=f2e379]:
                    - text: 买方收货地址
                    - textbox "买方收货地址" [ref=f2e380]:
                      - /placeholder: 未知
                  - generic [ref=f2e382]:
                    - text: 买方收件人
                    - textbox "买方收件人" [ref=f2e383]:
                      - /placeholder: 未知
                - generic [ref=f2e384]:
                  - heading "卖方" [level=4] [ref=f2e385]
                  - generic [ref=f2e387]:
                    - text: 卖方名称
                    - textbox "卖方名称" [ref=f2e388]:
                      - /placeholder: 未知
                  - generic [ref=f2e390]:
                    - text: 卖方国家 / 地区
                    - textbox "卖方国家 / 地区" [ref=f2e391]:
                      - /placeholder: 未知
                  - generic [ref=f2e393]:
                    - text: 卖方地址
                    - textbox "卖方地址" [ref=f2e394]:
                      - /placeholder: 未知
                  - generic [ref=f2e396]:
                    - text: 卖方税号
                    - textbox "卖方税号" [ref=f2e397]:
                      - /placeholder: 未知
                  - generic [ref=f2e399]:
                    - text: 卖方联系人
                    - textbox "卖方联系人" [ref=f2e400]:
                      - /placeholder: 未知
                  - generic [ref=f2e402]:
                    - text: 卖方电话
                    - textbox "卖方电话" [ref=f2e403]:
                      - /placeholder: 未知
                  - generic [ref=f2e405]:
                    - text: 卖方邮箱
                    - textbox "卖方邮箱" [ref=f2e406]:
                      - /placeholder: 未知
                  - generic [ref=f2e408]:
                    - text: 卖方账单地址
                    - textbox "卖方账单地址" [ref=f2e409]:
                      - /placeholder: 未知
                  - generic [ref=f2e411]:
                    - text: 卖方收货地址
                    - textbox "卖方收货地址" [ref=f2e412]:
                      - /placeholder: 未知
                  - generic [ref=f2e414]:
                    - text: 卖方收件人
                    - textbox "卖方收件人" [ref=f2e415]:
                      - /placeholder: 未知
              - button "保存双方资料" [ref=f2e416] [cursor=pointer]
            - generic [ref=f2e417]:
              - heading "报价概览" [level=3] [ref=f2e418]
              - generic [ref=f2e419]:
                - generic [ref=f2e420]:
                  - generic [ref=f2e421]: 报价总额
                  - strong [ref=f2e422]: USD 0.00
                - generic [ref=f2e423]:
                  - generic [ref=f2e424]: 有效期至
                  - strong [ref=f2e425]: —
                - generic [ref=f2e426]:
                  - generic [ref=f2e427]: 商品明细
                  - strong [ref=f2e428]: 0 项
            - generic [ref=f2e429]:
              - heading "基础信息" [level=3] [ref=f2e430]
              - generic [ref=f2e431]:
                - term [ref=f2e432]: 报价日期
                - definition [ref=f2e433]: 2026-11-05
                - term [ref=f2e434]: 币种 / 汇率
                - definition [ref=f2e435]: USD / 1
                - term [ref=f2e436]: 收件人
                - definition [ref=f2e437]: —
                - term [ref=f2e438]: 条款备注
                - definition [ref=f2e439]: —
            - generic [ref=f2e440]:
              - generic [ref=f2e441]:
                - generic [ref=f2e442]:
                  - heading "修订摘要" [level=3] [ref=f2e443]
                  - paragraph [ref=f2e448]: 共 1 个版本，当前查看 原始报价。
                - button "查看修订历史" [ref=f2e449] [cursor=pointer]
              - article [ref=f2e451]:
                - generic [ref=f2e452]:
                  - strong [ref=f2e453]: UIQ706064B8
                  - generic [ref=f2e454]: 原始报价
                  - generic [ref=f2e455]: 2026/11/05 20:58
                  - generic [ref=f2e456]: 草稿
                - generic [ref=f2e457]:
                  - text: USD 0.00
                  - generic [ref=f2e458]:
                    - button "预览 PI" [ref=f2e459] [cursor=pointer]
                    - button "查看详情" [disabled] [ref=f2e460] [cursor=pointer]
            - generic [ref=f2e461]:
              - heading "销售订单摘要" [level=3] [ref=f2e462]
              - paragraph [ref=f2e467]: 已生成 0 张销售订单。
              - button "查看关联销售订单" [ref=f2e468] [cursor=pointer]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import { spawnSync } from 'node:child_process'
  3  | import fs from 'node:fs'
  4  | import path from 'node:path'
  5  | 
  6  | test.use({ channel: 'chrome' })
  7  | test('draft party details can be saved and reopened on all three documents', async ({ page, baseURL }) => {
  8  |   expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  9  |   const root = path.resolve('../docs/uat-evidence/party-version-closeout-02')
  10 |   const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(root, 'seed_party_details_ui.py')], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
  11 |   expect(seed.status, seed.stderr).toBe(0)
  12 |   const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  13 |   await page.goto(`${process.env.ISOLATED_PLAYWRIGHT_API_BASE_URL}/admin/login/`)
  14 |   await page.locator('[name="username"]').fill(fixture.username)
  15 |   await page.locator('[name="password"]').fill('synthetic-only-password')
  16 |   await page.locator('input[type="submit"]').click()
  17 |   await expect(page).not.toHaveURL(/\/admin\/login/)
  18 |   const evidence = path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'party-details-ui')
  19 |   fs.mkdirSync(evidence, { recursive: true })
  20 |   for (const [kind, route] of [['quote', 'quotes'], ['order', 'orders'], ['purchase', 'purchase-orders']]) {
> 21 |     await page.goto(new URL(`/${route}?detail=${fixture[kind]}`, baseURL).toString())
     |                ^ Error: page.goto: Test timeout of 30000ms exceeded.
  22 |     const panel = page.locator('.party-details-panel')
  23 |     await expect(panel.getByRole('heading', { name: '草稿双方资料' })).toBeVisible()
  24 |     await panel.getByLabel('买方账单地址').fill(`Synthetic ${kind} billing`)
  25 |     await panel.getByLabel('卖方税号').fill('SYNTHETIC-TAX')
  26 |     const saved = page.waitForResponse(r => r.url().endsWith('/party-details/') && r.request().method() === 'PUT')
  27 |     await panel.getByRole('button', { name: '保存双方资料' }).click()
  28 |     expect((await saved).status()).toBe(200)
  29 |     await page.reload()
  30 |     await expect(panel.getByLabel('买方账单地址')).toHaveValue(`Synthetic ${kind} billing`)
  31 |     await expect(panel.getByLabel('卖方税号')).toHaveValue('SYNTHETIC-TAX')
  32 |     await page.screenshot({ path: path.join(evidence, `${kind}.png`), fullPage: true })
  33 |   }
  34 | })
  35 | 
```