# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: cash-duplicate-real.spec.js >> 核对同账户同额候选并有说明放行 390px
- Location: browser-tests\cash-duplicate-real.spec.js:23:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.preview-box')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" locator('.preview-box') with timeout 5000ms
  - waiting for locator('.preview-box')

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
    - link "数据导入":
      - /url: /import
    - text: 组织与系统
    - link "组织与权限":
      - /url: /organization
  - text: J
  - strong: 开发身份：Johnson
  - text: 超级管理员 · 全部功能与数据权限
- main:
  - button
  - text: Bank cash facts
  - heading "人民币资金" [level=1]
  - text: J
  - paragraph: 人民币实际资金
  - heading "银行资金记录" [level=2]
  - paragraph: 登记系统中的人民币银行资金事件；只有已确认的事件才纳入银行实际人民币资金汇总。结汇不新增客户收款，也不改变应收核销。
  - link "查看财务流水":
    - /url: /transactions
  - button "新建资金事件"
  - paragraph:
    - strong: 口径：
    - text: 只有人工核实银行凭证的事件可以确认。已确认仅表示本系统已登记且确认的银行事实，不代表公司全部银行余额；待确认资金不是已实际到账。参考折算只用于对照，不代表银行实际到账；手续费按银行净额说明，不重复扣除。
  - form "人民币资金筛选":
    - text: 状态
    - combobox "状态":
      - option "全部状态" [selected]
      - option "待确认"
      - option "已确认"
      - option "已放弃"
    - text: 搜索
    - searchbox "搜索"
    - button "刷新"
  - paragraph: 列表同时包含待确认、已确认和已放弃记录；只有已确认记录计入银行实际人民币资金。本页“银行日期”指银行实际入账 / 扣款日期；流水发生日期请在财务流水页查看。退款、反向更正和历史资金归属不会在本页自动处理，请按原始凭证核对。
  - table:
    - rowgroup:
      - row "银行日期 / 事件编号 类型 原币来源 银行净额 手续费 状态 操作":
        - columnheader "银行日期 / 事件编号"
        - columnheader "类型"
        - columnheader "原币来源"
        - columnheader "银行净额"
        - columnheader "手续费"
        - columnheader "状态"
        - columnheader "操作"
    - rowgroup:
      - row "2026-10-19 SYNTH-DUP-A-390 独立银行扣费 流出 CNY 5.00 1 条来源 CNY 5.00 SYNTH-REF-390 无 已确认 查看详情":
        - cell "2026-10-19 SYNTH-DUP-A-390"
        - cell "独立银行扣费 流出"
        - cell "CNY 5.00 1 条来源"
        - cell "CNY 5.00 SYNTH-REF-390"
        - cell "无"
        - cell "已确认"
        - cell "查看详情":
          - button "查看详情"
      - row "2026-10-18 SYNTH-DUP-A-1440 独立银行扣费 流出 CNY 5.00 1 条来源 CNY 5.00 SYNTH-REF-1440 无 已确认 查看详情":
        - cell "2026-10-18 SYNTH-DUP-A-1440"
        - cell "独立银行扣费 流出"
        - cell "CNY 5.00 1 条来源"
        - cell "CNY 5.00 SYNTH-REF-1440"
        - cell "无"
        - cell "已确认"
        - cell "查看详情":
          - button "查看详情"
  - dialog "新建人民币资金事件":
    - paragraph: 人工凭证流程
    - heading "新建人民币资金事件" [level=3]
    - paragraph: 先预览，再登记待确认草稿，最后单独确认银行凭证。
    - button "关闭资金表单": ×
    - group "银行交易资料（可选）":
      - text: 银行交易资料（可选） 交易对手
      - textbox "交易对手": 合成对手乙
      - text: 银行交易标识
      - textbox "银行交易标识": SYNTH-ID-B-390
      - text: 银行摘要
      - textbox "银行摘要": 合成银行摘要乙
      - paragraph: 按银行凭证填写；未知时留空，不从客户资料推测。
    - group "1. 事件与银行金额（待确认前）":
      - text: 1. 事件与银行金额（待确认前） 事件编号
      - textbox "事件编号": P2B-EVENT-f4b42bcd-9d88-4646-bb4e-586fd5bdb527
      - text: 稳定请求键
      - textbox "稳定请求键 重试必须沿用此编号。": P2B-REQUEST-5856434f-b18c-4482-95be-4dcd76aebea2
      - text: 重试必须沿用此编号。 事件类型
      - combobox "事件类型":
        - option "外币结汇流入"
        - option "人民币直接收付"
        - option "独立银行扣费" [selected]
      - text: 来源币种
      - combobox "来源币种":
        - option "CNY · 人民币" [selected]
        - option "USD · 美元"
        - option "EUR · 欧元"
        - option "GBP · 英镑"
        - option "HKD · 港币"
        - option "AUD · 澳元"
        - option "JPY · 日元"
      - text: 资金方向
      - combobox "资金方向":
        - option "流入"
        - option "流出" [selected]
      - text: 银行实际日期
      - textbox "银行实际日期": 2026-10-19
      - text: 银行净额（CNY）
      - spinbutton "银行净额（CNY） 以银行凭证净到账/扣款为准；待确认前仅是待核对金额。": "5"
      - text: 以银行凭证净到账/扣款为准；待确认前仅是待核对金额。 参考折算汇率
      - textbox "参考折算汇率 仅作差异对照，不覆盖银行净额；保留原始十进制输入。":
        - /placeholder: 可留空
        - text: "1"
      - text: 仅作差异对照，不覆盖银行净额；保留原始十进制输入。 手续费方式
      - combobox "手续费方式":
        - option "无含扣手续费" [selected]
        - option "净额已含扣费"
      - text: 关联结汇事件（可选）
      - combobox "关联结汇事件（可选） 与结汇有关时，请选择同一人民币账户的已确认结汇事件；无关的银行扣费可留空。":
        - option "不关联结汇" [selected]
      - text: 与结汇有关时，请选择同一人民币账户的已确认结汇事件；无关的银行扣费可留空。
    - group "2. 银行凭证与受控账户":
      - text: 2. 银行凭证与受控账户 来源银行账户标识
      - textbox "来源银行账户标识":
        - /placeholder: 例如 SYNTH-FX-01
        - text: SYNTH_CNY
      - text: 人民币账户标识
      - textbox "人民币账户标识":
        - /placeholder: 例如 SYNTH-CNY-01
        - text: SYNTH_CNY
      - text: 银行参考号
      - textbox "银行参考号": SYNTH-REF-B-390
      - text: 凭证引用
      - textbox "凭证引用":
        - /placeholder: 文件名或内部凭证编号
        - text: SYNTH-VOUCHER-B
      - text: 凭证 SHA256
      - textbox "凭证 SHA256":
        - /placeholder: 确认时必填
        - text: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
      - text: 人工核实说明
      - textbox "人工核实说明":
        - /placeholder: 确认时必填，记录核对人和核对内容
        - text: 合成凭证核对
      - paragraph: 账户标识仅用于后端受控校验，不填写银行登录信息。当前环境未配置账户时，确认会被安全阻止。
    - group "3. 来源分配":
      - text: 3. 来源分配
      - searchbox "搜索流水号"
      - button "刷新来源"
      - strong: SYNTH-FEE-C2CD401E-0 · CNY 5.00
      - text: 支出 · 可用 CNY 0.00
      - button "选择"
      - strong: SYNTH-FEE-C2CD401E-1 · CNY 5.00
      - text: 支出 · 可用 CNY 5.00
      - button "选择"
      - strong: SYNTH-FEE-C2CD401E-2 · CNY 5.00
      - text: 支出 · 可用 CNY 5.00
      - button "选择"
      - strong: SYNTH-FEE-C2CD401E-3 · CNY 5.00
      - text: 支出 · 可用 CNY 5.00
      - button "选择"
      - strong: SYNTH-FEE-31405DD0-0 · CNY 5.00
      - text: 支出 · 可用 CNY 5.00
      - button "选择"
      - strong: SYNTH-FEE-31405DD0-1 · CNY 5.00
      - text: 支出 · 可用 CNY 5.00
      - button "选择"
      - strong: SYNTH-FEE-31405DD0-2 · CNY 5.00
      - text: 支出 · 可用 CNY 0.00
      - button "选择"
      - strong: SYNTH-FEE-31405DD0-3 · CNY 5.00
      - text: 支出 · 可用 CNY 5.00
      - button "已选择" [disabled]
      - table:
        - rowgroup:
          - row "来源 可用额度 本次分配 人工核实":
            - columnheader "来源"
            - columnheader "可用额度"
            - columnheader "本次分配"
            - columnheader "人工核实"
            - columnheader
        - rowgroup:
          - row "SYNTH-FEE-31405DD0-3 CNY 5.00 已核实 移除":
            - cell "SYNTH-FEE-31405DD0-3"
            - cell "CNY 5.00"
            - cell:
              - spinbutton
            - cell "已核实":
              - checkbox "已核实" [checked]
              - text: 已核实
            - cell "移除":
              - button "移除"
      - paragraph: 已分配 CNY 0.00 · 银行净额 CNY 5.00
    - paragraph: 手续费口径：银行净额已含扣费时不要再次扣除；独立银行扣费使用单独的人民币手续费来源，关联结汇可选。
    - paragraph: 历史来源保留了更高精度，请按币种精度人工填写本次分配；系统不会自动舍入历史金额。
    - paragraph: 来源分配只保存本次逐条核实的归属，不会自动推定历史资金归属。
    - alert: 每条来源都要填写大于0的分配金额。
    - button "取消"
    - button "后端预览"
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import { spawnSync } from 'node:child_process'
  3  | import fs from 'node:fs'
  4  | import path from 'node:path'
  5  | 
  6  | test.use({ channel: 'chrome' })
  7  | const report = path.resolve('../docs/uat-evidence/r1-iss105-bank-duplicate-detection-20261103')
  8  | const seed = path.resolve('../docs/uat-evidence/r1-iss105-independent-bank-fee-fix-20261103/seed_browser.py')
  9  | const screenshots = path.join(report, 'screenshots')
  10 | const results = []
  11 | let fixture
  12 | 
  13 | test.beforeAll(() => {
  14 |   expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  15 |   const result = spawnSync(process.env.ISOLATED_TEST_PYTHON, [seed], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
  16 |   expect(result.status, result.stderr).toBe(0)
  17 |   fixture = JSON.parse(result.stdout.trim().split('\n').at(-1))
  18 |   fs.mkdirSync(screenshots, { recursive: true })
  19 | })
  20 | test.afterAll(() => fs.writeFileSync(path.join(report, 'browser-http.json'), JSON.stringify(results, null, 2)))
  21 | 
  22 | for (const [index, width] of [1440, 390].entries()) {
  23 |   test(`核对同账户同额候选并有说明放行 ${width}px`, async ({ page }) => {
  24 |     await page.setViewportSize({ width, height: 900 })
  25 |     const date = index ? '2026-10-19' : '2026-10-18'
  26 |     const data = { event_no: `SYNTH-DUP-A-${width}`, request_key: `SYNTH-DUP-A-${width}`, kind: 'bank_fee', currency: 'CNY', direction: 'expense', bank_date: date, bank_net_amount: '5.00', fee_mode: 'none', fee_amount: '0', source_account: 'SYNTH_CNY', rmb_account: 'SYNTH_CNY', bank_reference: `SYNTH-REF-${width}`, bank_counterparty: '合成对手甲', bank_summary: '合成银行摘要甲', bank_transaction_id: `SYNTH-ID-${width}`, evidence_reference: 'SYNTH-VOUCHER', evidence_sha256: 'a'.repeat(64), evidence_note: '合成银行凭证', quoted_rate: '1', fee_for: null, correction_of: null, sources: [{ transaction_id: fixture.fee_ids[index * 2], amount: '5.00', verified: true }] }
  27 |     const first = await page.request.post('/api/rmb-cash-events/', { data })
  28 |     expect(first.status()).toBe(201)
  29 |     const firstId = (await first.json()).id
  30 |     expect((await page.request.post(`/api/rmb-cash-events/${firstId}/confirm/`, { data: { voucher_checked: true } })).status()).toBe(200)
  31 |     page.on('response', async response => {
  32 |       if (!response.url().includes('/api/rmb-cash-events/')) return
  33 |       try { results.push({ width, method: response.request().method(), path: new URL(response.url()).pathname, status: response.status(), response: await response.json() }) } catch {}
  34 |     })
  35 |     await page.goto('/rmb-cash-events')
  36 |     await page.getByRole('button', { name: '新建资金事件' }).click()
  37 |     await page.getByLabel('事件类型').selectOption('bank_fee')
  38 |     await page.getByLabel('银行净额（CNY）').fill('5.00')
  39 |     await page.getByLabel('银行实际日期').fill(date)
  40 |     await page.getByLabel('来源银行账户标识').fill('SYNTH_CNY')
  41 |     await page.getByLabel('人民币账户标识').fill('SYNTH_CNY')
  42 |     await page.getByLabel('银行参考号').fill(`SYNTH-REF-B-${width}`)
  43 |     await page.getByLabel('交易对手').fill('合成对手乙')
  44 |     await page.getByLabel('银行摘要').fill('合成银行摘要乙')
  45 |     await page.getByLabel('银行交易标识').fill(`SYNTH-ID-B-${width}`)
  46 |     await page.getByLabel('凭证引用').fill('SYNTH-VOUCHER-B')
  47 |     await page.getByLabel('凭证 SHA256').fill('b'.repeat(64))
  48 |     await page.getByLabel('人工核实说明').fill('合成凭证核对')
  49 |     await page.locator('.source-option').filter({ hasText: fixture.fee_names[index * 2 + 1] }).getByRole('button', { name: '选择', exact: true }).click()
  50 |     await page.locator('.verification-toggle input').check()
  51 |     await page.getByRole('button', { name: '后端预览' }).click()
> 52 |     await expect(page.locator('.preview-box')).toBeVisible()
     |                                                ^ Error: expect(locator).toBeVisible() failed
  53 |     await expect(page.locator('.warning-box').filter({ hasText: '疑似重复' })).toBeVisible()
  54 |     await page.getByRole('button', { name: '登记待确认草稿' }).click()
  55 |     await page.getByRole('checkbox', { name: /我已核对以上银行凭证/ }).check()
  56 |     await page.getByRole('button', { name: '确认银行凭证' }).click()
  57 |     const box = page.locator('section.warning-box').filter({ hasText: '疑似重复' })
  58 |     await expect(box).toContainText('合成对手甲')
  59 |     await expect(box).toContainText('合成银行摘要甲')
  60 |     await expect(box).toContainText(`SYNTH-ID-${width}`)
  61 |     await box.scrollIntoViewIfNeeded()
  62 |     await page.screenshot({ path: path.join(screenshots, `duplicate-review-${width}.png`) })
  63 |     await page.getByLabel('核实放行说明').fill('已逐项核对银行凭证，确认是另一笔交易')
  64 |     await page.getByRole('button', { name: '确认银行凭证' }).click()
  65 |     await expect(page.locator('.review-banner')).toContainText('已确认')
  66 |   })
  67 | }
  68 | 
```