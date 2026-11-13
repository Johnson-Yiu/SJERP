# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: prelaunch-p1-05-feedback-02.spec.js >> P1-05 packaging and procurement pending failure recovery and persisted success
- Location: browser-tests\prelaunch-p1-05-feedback-02.spec.js:7:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('dialog', { name: '采购草稿预览' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('dialog', { name: '采购草稿预览' }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '采购草稿预览' })

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
    - link "银行资金记录":
      - /url: /rmb-cash-events
    - link "账户余额与对账":
      - /url: /finance-ledger
    - link "数据导入":
      - /url: /import
    - link "历史资料预检":
      - /url: /history-preflight
    - link "历史资料承接":
      - /url: /history-takeover
    - text: 组织与系统
    - link "组织与权限":
      - /url: /organization
  - text: C
  - strong: 当前账号：codex
  - text: 超级管理员 · 全部功能与数据权限
  - button "退出登录"
- main:
  - text: Sales orders
  - heading "订单管理" [level=1]
  - text: 11月14日周六 C
  - tablist "业务工作区":
    - tab "SYNTH-SALES-PROCUREMENT-20261110" [selected]
    - button "关闭 SYNTH-SALES-PROCUREMENT-20261110": ×
    - button "SYNTH-SALES-PROCUREMENT-20261110 标签操作": ⋮
  - tabpanel "SYNTH-SALES-PROCUREMENT-20261110":
    - paragraph: 管理销售订单、履约与回款。
    - button "新建订单"
    - region "页面小计":
      - article:
        - text: 执行中
        - strong: "1"
        - text: 已确认 / 生产中 / 已发货
      - article:
        - text: 待出库
        - strong: "1"
        - text: 尚未完成发货
      - article:
        - text: 待收款
        - strong: "0"
        - text: 仍有应收余额
      - article:
        - text: 已完成
        - strong: "1"
        - text: 已完成交付
    - textbox "搜索订单号或客户"
    - combobox "按订单状态筛选":
      - option "全部状态" [selected]
      - option "草稿"
      - option "已确认"
      - option "生产中"
      - option "已发货"
      - option "已完成"
      - option "已取消"
    - combobox "按订单待办筛选":
      - option "全部待办" [selected]
      - option "待出库"
      - option "交期已到"
    - button "重置"
    - table:
      - rowgroup:
        - row "订单号 客户 订单日期 预计出货日期 履约状态 明细 订单总额 已收 / 待收 操作":
          - columnheader "订单号"
          - columnheader "客户"
          - columnheader "订单日期"
          - columnheader "预计出货日期"
          - columnheader "履约状态"
          - columnheader "明细"
          - columnheader "订单总额"
          - columnheader "已收 / 待收"
          - columnheader "操作"
      - rowgroup:
        - row "SYNTH-SALES-PROCUREMENT-20261110 历史主体未记录 2026-11-10 未设置 已确认 1 项 USD 187.50 0.00 / 应收计划待核对":
          - cell "SYNTH-SALES-PROCUREMENT-20261110"
          - cell "历史主体未记录"
          - cell "2026-11-10"
          - cell "未设置"
          - cell "已确认"
          - cell "1 项"
          - cell "USD 187.50"
          - cell "0.00 / 应收计划待核对"
          - cell
        - row "SYNTH-SALES-COMPLETED-20261110-00000000001 历史主体未记录 2026-11-10 未设置 已完成 4 项 USD 1,250.00 0.00 / 应收计划待核对":
          - cell "SYNTH-SALES-COMPLETED-20261110-00000000001"
          - cell "历史主体未记录"
          - cell "2026-11-10"
          - cell "未设置"
          - cell "已完成"
          - cell "4 项"
          - cell "USD 1,250.00"
          - cell "0.00 / 应收计划待核对"
          - cell
        - row "SYNTH-SALES-ORDER-20261110-00000000001 SYNTH-SALES 森爵界面验收国际商业照明与综合工程采购服务中心 — International Commercial Lighting Project Procurement 2026-11-10 未设置 草稿 4 项 USD 1,250.00 0.00 / 尚未生效 编辑 SYNTH-SALES-ORDER-20261110-00000000001 删除 SYNTH-SALES-ORDER-20261110-00000000001":
          - cell "SYNTH-SALES-ORDER-20261110-00000000001"
          - cell "SYNTH-SALES 森爵界面验收国际商业照明与综合工程采购服务中心 — International Commercial Lighting Project Procurement"
          - cell "2026-11-10"
          - cell "未设置"
          - cell "草稿"
          - cell "4 项"
          - cell "USD 1,250.00"
          - cell "0.00 / 尚未生效"
          - cell "编辑 SYNTH-SALES-ORDER-20261110-00000000001 删除 SYNTH-SALES-ORDER-20261110-00000000001":
            - button "编辑 SYNTH-SALES-ORDER-20261110-00000000001"
            - button "删除 SYNTH-SALES-ORDER-20261110-00000000001"
    - dialog "订单工作台":
      - button "关闭订单详情": 关闭
      - text: 订单工作台 · 履约与回款
      - button "开始生产"
      - button "取消订单"
      - paragraph: 历史主体未记录 · 下单于 2026-11-10
      - heading "SYNTH-SALES-PROCUREMENT-20261110" [level=2]
      - text: 预计交期：未设置 履约：已确认
      - main:
        - navigation "订单工作台分页":
          - button "概览"
          - button "订单明细 (1)"
          - button "采购与发货"
          - button "回款 (0)"
          - button "装箱"
          - button "库存流水 (0)"
          - button "操作日志 (0)"
      - heading "采购与发货" [level=3]
      - paragraph: 采购草稿不计入已采购。
      - button "批量发货"
      - button "生成采购草稿"
      - region "履约状态摘要":
        - article:
          - text: 待采购 SKU
          - strong: "1"
        - article:
          - text: 采购中 SKU
          - strong: "0"
        - article:
          - text: 待发货明细
          - strong: "1"
        - article:
          - text: 已完成明细
          - strong: "0"
      - region "SKU 履约明细":
        - heading "SKU 履约明细" [level=3]
        - paragraph: 数量按 SKU 基础单位显示。
        - table:
          - rowgroup:
            - row "SKU / 当前状态 采购来源 订单需求 采购进度 到货进度 发货进度 操作":
              - columnheader "SKU / 当前状态"
              - columnheader "采购来源"
              - columnheader "订单需求"
              - columnheader "采购进度"
              - columnheader "到货进度"
              - columnheader "发货进度"
              - columnheader "操作"
          - rowgroup:
            - 'row "SYNTH-PROCUREMENT Synthetic commercial lighting · SYNTH-PROCUREMENT 基础单位：pcs 明细 #9 · 基础单位 待采购 合成采购来源 SYNTH-PROC-SUPPLIER 订单 15 pcs 已预留 0 pcs 待采购 15 pcs 可建草稿 15 pcs — 已发 0 pcs 待发 15 pcs 确认发货 更换来源"':
              - 'cell "SYNTH-PROCUREMENT Synthetic commercial lighting · SYNTH-PROCUREMENT 基础单位：pcs 明细 #9 · 基础单位 待采购"':
                - strong: SYNTH-PROCUREMENT
                - text: "Synthetic commercial lighting · SYNTH-PROCUREMENT 基础单位：pcs 明细 #9 · 基础单位 待采购"
              - cell "合成采购来源 SYNTH-PROC-SUPPLIER":
                - strong: 合成采购来源
                - text: SYNTH-PROC-SUPPLIER
              - cell "订单 15 pcs 已预留 0 pcs":
                - strong: 订单 15 pcs
                - text: 已预留 0 pcs
              - cell "待采购 15 pcs 可建草稿 15 pcs":
                - strong: 待采购 15 pcs
                - text: 可建草稿 15 pcs
              - cell "—"
              - cell "已发 0 pcs 待发 15 pcs":
                - text: 已发 0 pcs
                - strong: 待发 15 pcs
              - cell "确认发货 更换来源":
                - button "确认发货"
                - button "更换来源"
      - heading "关联采购单" [level=3]
      - paragraph: 采购草稿不计入已下单数量。
      - strong: 尚未创建关联采购单
      - paragraph: 请先选择采购来源，再生成采购草稿。
      - heading "发货记录" [level=3]
      - paragraph: 整单冲销会同步撤销关联的超发或增补记录。
      - strong: 0 条
      - strong: 暂无发货记录
      - paragraph: 有可发库存后，可在明细中确认发货。
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test'
  2   | import { execFileSync } from 'node:child_process'
  3   | import { mkdir, readFile, writeFile } from 'node:fs/promises'
  4   | import path from 'node:path'
  5   | 
  6   | test.use({ channel: 'chrome', viewport: { width: 1366, height: 768 } })
  7   | test('P1-05 packaging and procurement pending failure recovery and persisted success', async ({ page, browser }, info) => {
  8   |   test.setTimeout(240000)
  9   |   const output = info.outputPath('p1-05')
  10  |   await mkdir(output, { recursive: true })
  11  |   const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.resolve('../docs/uat-evidence/ui-sales-completion-02/seed.py')], { env: process.env, encoding: 'utf8' }))
  12  |   const results = []
  13  |   const capture = async state => {
  14  |     for (const [width, height] of [[1366, 768], [1920, 1080]]) {
  15  |       await page.setViewportSize({ width, height })
  16  |       await page.screenshot({ path: path.join(output, `${state}-${width}.png`) })
  17  |       expect(await page.evaluate(() => devicePixelRatio)).toBe(1)
  18  |     }
  19  |     await page.setViewportSize({ width: 1366, height: 768 })
  20  |   }
  21  |   await page.goto('/quotes?create=1&customer=' + fixture.customer)
  22  |   const editor = page.getByRole('form', { name: '报价编辑器' })
  23  |   await editor.locator('.sku-picker-options label').filter({ hasText: 'SYNTH-SALES-SKU-001' }).getByRole('checkbox').check()
  24  |   await editor.getByRole('button', { name: '生成预计装箱方案' }).click()
  25  |   await editor.getByRole('button', { name: /补充默认包装/ }).click()
  26  |   const packaging = page.locator('.packaging-config-modal')
  27  |   await packaging.locator('select').selectOption(String(fixture.carton))
  28  |   await packaging.getByRole('spinbutton').nth(0).fill('5')
  29  |   await packaging.getByRole('spinbutton').nth(1).fill('0.5')
  30  |   let releasePackaging
  31  |   const packagingHeld = new Promise(resolve => { releasePackaging = resolve })
  32  |   await page.route('**/api/skus/*/packaging/', async route => {
  33  |     if (route.request().method() !== 'PUT') return route.continue()
  34  |     await packagingHeld
  35  |     await route.fulfill({ status: 503, json: { detail: '合成包装保存失败，请重试。' } })
  36  |   })
  37  |   await packaging.getByRole('button', { name: '保存默认包装' }).click()
  38  |   await expect(packaging.getByRole('button', { name: '保存中...' })).toBeDisabled()
  39  |   await expect(packaging.getByRole('button', { name: '取消' })).toBeDisabled()
  40  |   await capture('packaging-pending')
  41  |   releasePackaging()
  42  |   await expect(packaging.getByRole('alert')).toContainText('默认包装保存失败')
  43  |   await expect(packaging.getByRole('spinbutton').first()).toHaveValue('5')
  44  |   await capture('packaging-failed')
  45  |   await page.unroute('**/api/skus/*/packaging/')
  46  |   const packaged = page.waitForResponse(r => r.url().endsWith('/packaging/') && r.request().method() === 'PUT')
  47  |   await packaging.getByRole('button', { name: '保存默认包装' }).click()
  48  |   const packagingResponse = await packaged
  49  |   expect(packagingResponse.status()).toBe(200)
  50  |   const packagingReadback = await page.request.get(packagingResponse.url())
  51  |   expect(packagingReadback.status()).toBe(200)
  52  |   const pack = await packagingReadback.json()
  53  |   expect(Number(pack.effective.effective_qty_per_carton)).toBe(5)
  54  |   await expect(packaging).toHaveCount(0)
  55  |   await capture('packaging-success')
  56  |   results.push({ key: 'packaging', save: 200, readback: pack })
  57  |   await editor.getByRole('button', { name: '取消', exact: true }).click()
  58  |   await page.getByRole('button', { name: '放弃修改', exact: true }).click()
  59  | 
  60  |   await page.goto('/orders?detail=' + fixture.procurementOrder)
  61  |   const workbench = page.getByRole('dialog', { name: '订单工作台' })
  62  |   await workbench.getByRole('button', { name: '采购与发货', exact: true }).click()
  63  |   await page.getByRole('button', { name: '生成采购草稿', exact: true }).click()
  64  |   const drawer = page.getByRole('dialog', { name: '采购草稿预览' })
  65  |   let releasePurchase
  66  |   const purchaseHeld = new Promise(resolve => { releasePurchase = resolve })
  67  |   await page.route('**/generate-purchase-drafts/', async route => {
  68  |     await purchaseHeld
  69  |     await route.fulfill({ status: 503, json: { detail: '合成采购草稿创建失败，请重试。' } })
  70  |   })
  71  |   await drawer.getByRole('button', { name: '创建 采购草稿' }).click()
  72  |   await expect(drawer.getByRole('button', { name: '创建中…' })).toBeDisabled()
  73  |   await capture('procurement-pending')
  74  |   // A pending write must not lose its result by closing the drawer.
  75  |   try {
  76  |     await drawer.getByRole('button', { name: '关闭', exact: true }).click()
> 77  |     await expect(drawer).toBeVisible()
      |                          ^ Error: expect(locator).toBeVisible() failed
  78  |   } finally { releasePurchase() }
  79  |   await expect(drawer.getByRole('alert')).toContainText('合成采购草稿创建失败')
  80  |   await capture('procurement-failed')
  81  |   await page.unroute('**/generate-purchase-drafts/')
  82  |   const created = page.waitForResponse(r => r.url().endsWith('/generate-purchase-drafts/') && r.request().method() === 'POST')
  83  |   await drawer.getByRole('button', { name: '创建 采购草稿' }).click()
  84  |   const response = await created
  85  |   expect(response.status()).toBe(201)
  86  |   const body = await response.json()
  87  |   expect(body.created_count).toBe(1)
  88  |   const draft = body.purchase_orders[0]
  89  |   const readback = await page.request.get(`/api/purchase-orders/${draft.id}/`)
  90  |   const record = await readback.json()
  91  |   expect(record.status).toBe('draft')
  92  |   expect(Number(record.items[0].quantity)).toBe(15)
  93  |   await expect(drawer).toHaveCount(0)
  94  |   await expect(workbench.getByRole('link', { name: draft.purchase_no })).toBeVisible()
  95  |   await capture('procurement-success')
  96  |   await page.reload()
  97  |   await workbench.getByRole('button', { name: '采购与发货', exact: true }).click()
  98  |   await expect(page.getByRole('button', { name: '生成采购草稿', exact: true })).toBeDisabled()
  99  |   results.push({ key: 'procurement', save: 201, id: draft.id, quantity: record.items[0].quantity, reopenedCannotDuplicate: true })
  100 |   await writeFile(path.join(output, 'result.json'), JSON.stringify({ source: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(), browser: browser.version(), results }, null, 2))
  101 | })
  102 | 
  103 | test('authenticated codex superuser imports XLSX and downloads the actual error CSV', async ({ page }) => {
  104 |   test.setTimeout(180000)
  105 |   const evidenceDir = path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'browser', 'sales-order-import-real.spec')
  106 |   await mkdir(evidenceDir, { recursive: true })
  107 |   execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.resolve('../backend/test_support/seed_sales_order_import_browser.py')], {
  108 |     cwd: path.resolve('../backend'), env: { ...process.env, SALES_ORDER_IMPORT_EVIDENCE_DIR: evidenceDir }, encoding: 'utf8',
  109 |   })
  110 |   const capture = async state => {
  111 |     for (const [width, height] of [[1366, 768], [1920, 1080]]) {
  112 |       await page.setViewportSize({ width, height })
  113 |       await page.screenshot({ path: path.join(evidenceDir, `${state}-${width}.png`) })
  114 |       expect(await page.evaluate(() => devicePixelRatio)).toBe(1)
  115 |     }
  116 |     await page.setViewportSize({ width: 1366, height: 768 })
  117 |   }
  118 |   const identityResponse = await page.request.get('/api/session/current-operator/')
  119 |   expect(identityResponse.status()).toBe(200)
  120 |   const identity = await identityResponse.json()
  121 |   expect(identity).toMatchObject({
  122 |     name: 'codex',
  123 |     role: '超级管理员',
  124 |     authenticated: true,
  125 |     development_superadmin: false,
  126 |     rbac_enforcement: false,
  127 |     has_all_permissions: true,
  128 |   })
  129 | 
  130 |   const fixture = JSON.parse(await readFile(path.join(evidenceDir, 'fixture.json'), 'utf8'))
  131 |   const workbookPath = path.join(evidenceDir, fixture.workbook)
  132 |   await page.goto('/import')
  133 |   await page.getByRole('tab', { name: '销售订单', exact: true }).click()
  134 | 
  135 |   const templateDownloadPromise = page.waitForEvent('download')
  136 |   await page.getByRole('button', { name: /下载销售订单 XLSX 模板/ }).click()
  137 |   const templateDownload = await templateDownloadPromise
  138 |   expect(templateDownload.suggestedFilename()).toBe('sales-order-import-template.xlsx')
  139 |   const templatePath = path.join(evidenceDir, templateDownload.suggestedFilename())
  140 |   await templateDownload.saveAs(templatePath)
  141 |   const templateBytes = await readFile(templatePath)
  142 |   expect(templateBytes.subarray(0, 2).toString('hex')).toBe('504b')
  143 | 
  144 |   await page.locator('input[type="file"][accept*=".xlsx"]').setInputFiles(workbookPath)
  145 |   await page.getByRole('button', { name: '预览并校验', exact: true }).click()
  146 |   await page.getByText('共 3 条明细、2 张订单：1 张可导入，1 张待修正', { exact: true }).waitFor()
  147 |   await page.getByText(`找不到 SKU：${fixture.invalid_sku}。`, { exact: true }).waitFor()
  148 | 
  149 |   let savedResult, resolveSaved, releaseResponse
  150 |   const saved = new Promise(resolve => { resolveSaved = resolve })
  151 |   const released = new Promise(resolve => { releaseResponse = resolve })
  152 |   await page.route('**/api/import/orders/execute/', async route => {
  153 |     const token = route.request().postData().match(/name="preview_token"\r\n\r\n([^\r\n]+)/)?.[1]
  154 |     expect(token).toBeTruthy()
  155 |     const response = await page.request.post(route.request().url(), { headers: { 'X-CSRFToken': route.request().headers()['x-csrftoken'] }, multipart: { file: { name:path.basename(workbookPath), mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer:await readFile(workbookPath) }, preview_token:token } })
  156 |     savedResult = await response.json(); await writeFile(path.join(evidenceDir, 'lost-response-result.json'), JSON.stringify({status:response.status(),body:savedResult},null,2)); resolveSaved()
  157 |     await released; await route.abort('failed')
  158 |   })
  159 |   await page.getByRole('button', { name: '确认导入 1 张草稿', exact: true }).click()
  160 |   const dialog = page.getByRole('dialog')
  161 |   await expect(dialog).toContainText('导入不会确认订单、占库存、生成应收计划或登记发货。')
  162 |   await page.getByRole('button', {name:'关闭 数据导入',exact:true}).press('Enter')
  163 |   await expect(dialog).toBeVisible()
  164 |   await page.getByTestId('dialog-confirm').click()
  165 |   await saved
  166 |   await capture('import-pending')
  167 |   await page.getByRole('button', {name:'关闭 数据导入',exact:true}).press('Enter')
  168 |   await expect(page.getByRole('tab', {name:'数据导入',exact:true})).toBeVisible()
  169 |   releaseResponse()
  170 |   await page.getByRole('alert').filter({hasText:'提交结果待核对'}).waitFor()
  171 |   await capture('import-lost-response')
  172 |   await page.unroute('**/api/import/orders/execute/')
  173 |   await page.reload()
  174 |   await page.getByRole('tab', {name:'销售订单',exact:true}).click()
  175 |   await page.locator('input[type="file"][accept*=".xlsx"]').setInputFiles(workbookPath)
  176 |   await expect(page.getByRole('alert').filter({ hasText: '已恢复待核对导入批次' })).toBeVisible()
  177 |   const executeResponsePromise = page.waitForResponse(response => new URL(response.url()).pathname === '/api/import/orders/execute/' && response.request().method() === 'POST')
```