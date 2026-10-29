# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: quote-editor-mobile-actions.spec.js >> quote editor actions stay readable at desktop and narrow widths and preserve preview/save/export
- Location: browser-tests\quote-editor-mobile-actions.spec.js:10:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: expect(locator).toBeVisible() failed

Locator: locator('form.quote-editor-modal').locator('.quote-action-save-export')
Expected: visible
Error: Test timeout of 30000ms exceeded.

Call log:
  - Expect "toBeVisible" locator('form.quote-editor-modal').locator('.quote-action-save-export') with timeout 5000ms
  - waiting for locator('form.quote-editor-modal').locator('.quote-action-save-export')
  - Test timeout of 30000ms exceeded.

```

# Page snapshot

```yaml
- generic [ref=f2e3]:
  - complementary [ref=f2e4]:
    - generic [ref=f2e5]:
      - generic [ref=f2e6]: S
      - generic [ref=f2e7]:
        - strong [ref=f2e8]: 森爵业务中台
        - text: CRM · ERP
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
      - link "数据导入" [ref=f2e170] [cursor=pointer]:
        - /url: /import
      - generic [ref=f2e175]: 组织与系统
      - link "组织与权限" [ref=f2e176] [cursor=pointer]:
        - /url: /organization
    - generic [ref=f2e181]:
      - generic [ref=f2e182]: J
      - generic [ref=f2e184]:
        - strong [ref=f2e185]: 开发身份：Johnson
        - generic [ref=f2e186]: 超级管理员 · 全部功能与数据权限
  - main [ref=f2e187]:
    - generic [ref=f2e188]:
      - button [ref=f2e189] [cursor=pointer]
      - generic [ref=f2e191]:
        - text: Quotation desk
        - heading "报价管理" [level=1] [ref=f2e192]
      - generic "Johnson" [ref=f2e194]: J
    - generic [ref=f2e196]:
      - generic [ref=f2e197]:
        - paragraph [ref=f2e198]: 管理报价版本、状态和成交转单。
        - button "新建报价" [ref=f2e199] [cursor=pointer]
      - region "报价汇总" [ref=f2e201]:
        - article [ref=f2e202]:
          - generic [ref=f2e203]: 报价项目
          - strong [ref=f2e204]: "1"
          - generic [ref=f2e208]: 报价主单数
        - article [ref=f2e209]:
          - generic [ref=f2e210]: 报价版本
          - strong [ref=f2e211]: "1"
          - generic [ref=f2e216]: 含所有修订版
        - article [ref=f2e217]:
          - generic [ref=f2e218]: 进行中
          - strong [ref=f2e219]: "1"
          - generic [ref=f2e224]: 草稿或已发送
        - article [ref=f2e225]:
          - generic [ref=f2e226]: 已接受
          - strong [ref=f2e227]: "0"
          - generic [ref=f2e232]: 客户已接受
      - generic [ref=f2e233]:
        - textbox "搜索报价单号或客户..." [ref=f2e238]
        - combobox "按报价状态筛选" [ref=f2e239]:
          - option "全部状态" [selected]
          - option "草稿"
          - option "已发送"
          - option "已接受"
          - option "已拒绝"
          - option "已过期"
        - combobox "按客户筛选" [ref=f2e240]:
          - option "全部客户"
          - option "报价操作验收客户" [selected]
        - combobox "报价排序" [ref=f2e241]:
          - option "最近更新时间" [selected]
          - option "最早更新时间"
          - option "报价日期（新到旧）"
          - option "报价日期（旧到新）"
        - button "重置" [ref=f2e242] [cursor=pointer]
      - table [ref=f2e248]:
        - rowgroup [ref=f2e249]:
          - row [ref=f2e250]:
            - columnheader "报价单 / 层级" [ref=f2e251]
            - columnheader "客户" [ref=f2e252]
            - columnheader "更新时间" [ref=f2e253]
            - columnheader "状态" [ref=f2e254]
            - columnheader "明细" [ref=f2e255]
            - columnheader "金额" [ref=f2e256]
            - columnheader "操作" [ref=f2e257]
        - rowgroup [ref=f2e258]:
          - row [ref=f2e259] [cursor=pointer]:
            - cell "SJ20261029DE001 原始报价" [ref=f2e260]:
              - generic [ref=f2e266]:
                - strong [ref=f2e267]: SJ20261029DE001
                - generic [ref=f2e268]: 原始报价
            - cell "报价操作验收客户" [ref=f2e269]
            - cell "2026/10/29 21:42" [ref=f2e270]
            - cell "草稿" [ref=f2e271]
            - cell "1 项" [ref=f2e273]
            - cell "USD 12.50" [ref=f2e274]
            - cell [ref=f2e275]:
              - generic [ref=f2e276]:
                - button "查看 SJ20261029DE001" [ref=f2e277]
                - button "创建修订版 SJ20261029DE001" [ref=f2e281]
                - button "导出 SJ20261029DE001" [ref=f2e285]
      - form "报价编辑器" [ref=f2e290]:
        - generic [ref=f2e291]:
          - generic [ref=f2e292]:
            - heading "新建报价" [level=3] [ref=f2e293]
            - generic [ref=f2e294]: 报价草稿
          - button "关闭报价编辑器" [ref=f2e295] [cursor=pointer]
        - group [ref=f2e300]:
          - generic [ref=f2e301]:
            - generic [ref=f2e302]:
              - generic [ref=f2e303]: 客户 *
              - combobox [disabled] [ref=f2e304]:
                - option "请选择"
                - option "报价操作验收客户" [selected]
            - generic [ref=f2e305]:
              - generic [ref=f2e306]: 报价单号
              - textbox [disabled] [ref=f2e307]: 保存后自动生成
            - generic [ref=f2e308]:
              - generic [ref=f2e309]: 报价日期 *
              - generic [ref=f2e310]:
                - textbox "年份" [ref=f2e311]: "2026"
                - generic [ref=f2e312]: /
                - textbox "月份" [ref=f2e313]: "10"
                - generic [ref=f2e314]: /
                - textbox "日期" [ref=f2e315]: "29"
                - button "打开日期选择器" [ref=f2e316] [cursor=pointer]
                - textbox: 2026-10-29
            - generic [ref=f2e319]:
              - generic [ref=f2e320]: 有效期
              - generic [ref=f2e321]:
                - spinbutton "有效期天数" [ref=f2e322]: "30"
                - generic [ref=f2e323]: 天
                - generic [ref=f2e324]:
                  - textbox "年份" [ref=f2e325]: "2026"
                  - generic [ref=f2e326]: /
                  - textbox "月份" [ref=f2e327]: "11"
                  - generic [ref=f2e328]: /
                  - textbox "日期" [ref=f2e329]: "28"
                  - button "打开日期选择器" [ref=f2e330] [cursor=pointer]
                  - textbox: 2026-11-28
            - generic [ref=f2e333]:
              - generic [ref=f2e334]: 状态
              - textbox [ref=f2e335]: 草稿
            - generic [ref=f2e336]:
              - generic [ref=f2e337]: 币种
              - combobox "单据币种" [ref=f2e338]:
                - option "USD" [selected]
                - option "CNY"
                - option "EUR"
                - option "GBP"
            - generic [ref=f2e339]:
              - generic [ref=f2e340]: 对人民币汇率
              - spinbutton "对人民币汇率" [ref=f2e341]: "7.2"
            - generic [ref=f2e342]:
              - generic [ref=f2e343]: 交期（天）
              - spinbutton [ref=f2e344]: "10"
            - generic [ref=f2e345]:
              - generic [ref=f2e346]: 定金比例（%）
              - spinbutton [ref=f2e347]: "30"
          - generic [ref=f2e349]:
            - strong [ref=f2e350]: 产品明细
            - generic [ref=f2e351]: 选择 SKU 后填写数量、交易单位和单价。
          - generic [ref=f2e352]:
            - generic [ref=f2e353]:
              - generic [ref=f2e354]:
                - strong [ref=f2e355]: 选择 SKU
                - generic [ref=f2e356]:
                  - searchbox "搜索 SKU、型号或描述" [ref=f2e357]
                  - button "按产品分类筛选" [ref=f2e358] [cursor=pointer]:
                    - generic [ref=f2e359]: 全部分类
              - generic [ref=f2e363] [cursor=pointer]:
                - 'checkbox "报价操作验收灯具 SKU: R1-UX-QA-SKU Sales Model: R1-QA-MODEL USD 12.50" [ref=f2e364]'
                - generic [ref=f2e365]:
                  - generic [ref=f2e366]: 报价操作验收灯具
                  - generic [ref=f2e367]:
                    - generic [ref=f2e368]: "SKU: R1-UX-QA-SKU"
                    - generic [ref=f2e369]: "Sales Model: R1-QA-MODEL"
                - emphasis [ref=f2e370]: USD 12.50
            - complementary [ref=f2e371]:
              - paragraph [ref=f2e372]: 从左侧勾选 SKU 后，可在这里查看详情。
          - paragraph [ref=f2e373]: 请先从上方选择至少一个 SKU。
          - generic [ref=f2e374]:
            - generic [ref=f2e375]:
              - text: 运费
              - spinbutton "运费" [ref=f2e376]: "0.00"
            - generic [ref=f2e377]:
              - text: 折扣
              - spinbutton "折扣" [ref=f2e378]: "0.00"
            - generic [ref=f2e379]:
              - text: 商品小计 USD 0.00
              - generic [ref=f2e380]: 合计
              - strong [ref=f2e381]: USD 0.00
          - strong [ref=f2e383]: 收件信息 / 条款
          - generic [ref=f2e384]:
            - generic [ref=f2e385]:
              - generic [ref=f2e386]: 收件人
              - textbox "收件人" [ref=f2e387]: 报价操作验收客户
            - generic [ref=f2e388]:
              - generic [ref=f2e389]: 买方地址
              - textbox "买方地址" [ref=f2e390]: Synthetic Test Address
            - generic [ref=f2e391]:
              - generic [ref=f2e392]: 买方邮箱
              - textbox "买方邮箱" [ref=f2e393]
            - generic [ref=f2e394]:
              - generic [ref=f2e395]: 买方电话
              - textbox "买方电话" [ref=f2e396]
          - generic [ref=f2e397]:
            - generic [ref=f2e398]:
              - generic [ref=f2e399]: 贸易条款
              - textbox [ref=f2e400]: FOB Shenzhen
            - generic [ref=f2e401]:
              - generic [ref=f2e402]: 运输信息
              - textbox [ref=f2e403]
            - generic [ref=f2e404]:
              - generic [ref=f2e405]: 附加备注
              - textbox [ref=f2e406]
        - generic [ref=f2e407]:
          - button "取消" [ref=f2e408] [cursor=pointer]
          - button "预览报价单" [ref=f2e409] [cursor=pointer]
          - button "保存报价" [ref=f2e413] [cursor=pointer]
          - button "保存并导出 Excel" [ref=f2e418] [cursor=pointer]
```

# Test source

```ts
  1   | import { expect, test } from '@playwright/test'
  2   | import fs from 'node:fs/promises'
  3   | import path from 'node:path'
  4   | 
  5   | const evidenceDir = path.resolve(process.env.R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR || '')
  6   | if (!process.env.R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR) {
  7   |   throw new Error('R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR must point to the task evidence directory.')
  8   | }
  9   | 
  10  | test('quote editor actions stay readable at desktop and narrow widths and preserve preview/save/export', async ({ page }) => {
  11  |   await fs.mkdir(evidenceDir, { recursive: true })
  12  |   const fixture = JSON.parse(await fs.readFile(path.join(evidenceDir, 'fixture.json'), 'utf8'))
  13  |   expect(fixture.synthetic_only).toBe(true)
  14  |   const apiResponses = []
  15  |   page.on('response', response => {
  16  |     if (new URL(response.url()).pathname.startsWith('/api/quotes/')) {
  17  |       apiResponses.push({ method: response.request().method(), path: new URL(response.url()).pathname, status: response.status() })
  18  |     }
  19  |   })
  20  | 
  21  |   async function openEditor() {
  22  |     await page.goto(`/quotes?create=1&customer=${fixture.customer}`)
  23  |     const editor = page.locator('form.quote-editor-modal')
  24  |     await expect(editor).toBeVisible()
> 25  |     await expect(editor.locator('.quote-action-save-export')).toBeVisible()
      |                                                               ^ Error: expect(locator).toBeVisible() failed
  26  |     return editor
  27  |   }
  28  | 
  29  |   // The original cancel action remains available and closes a clean editor.
  30  |   await page.setViewportSize({ width: 1440, height: 1000 })
  31  |   let editor = await openEditor()
  32  |   await editor.getByRole('button', { name: '取消', exact: true }).click()
  33  |   await expect(editor).toHaveCount(0)
  34  | 
  35  |   editor = await openEditor()
  36  |   await editor.locator('.sku-picker-options label').filter({ hasText: 'R1-UX-QA-SKU' }).locator('input[type="checkbox"]').check()
  37  |   await expect(editor.locator('.quote-line-row')).toHaveCount(1)
  38  | 
  39  |   const layouts = []
  40  |   for (const width of [1440, 1024, 390, 320]) {
  41  |     await page.setViewportSize({ width, height: 900 })
  42  |     const footer = editor.locator('.quote-editor-actions')
  43  |     await footer.scrollIntoViewIfNeeded()
  44  |     const measurements = await footer.evaluate(node => {
  45  |       const footerRect = node.getBoundingClientRect()
  46  |       const actions = [...node.querySelectorAll('button')].map(button => {
  47  |         const rect = button.getBoundingClientRect()
  48  |         return {
  49  |           className: [...button.classList].find(name => name.startsWith('quote-action-')),
  50  |           text: button.innerText.replace(/\s+/g, ' ').trim(),
  51  |           x: rect.x,
  52  |           y: rect.y,
  53  |           width: rect.width,
  54  |           height: rect.height,
  55  |           right: rect.right,
  56  |           visible: rect.width > 0 && rect.height > 0,
  57  |           textFits: button.scrollWidth <= button.clientWidth + 1,
  58  |         }
  59  |       })
  60  |       return {
  61  |         viewport: innerWidth,
  62  |         footer: { x: footerRect.x, right: footerRect.right, width: footerRect.width, scrollWidth: node.scrollWidth, clientWidth: node.clientWidth },
  63  |         actions,
  64  |       }
  65  |     })
  66  |     expect(measurements.actions.map(action => action.className)).toEqual([
  67  |       'quote-action-cancel', 'quote-action-preview', 'quote-action-save', 'quote-action-save-export',
  68  |     ])
  69  |     for (const action of measurements.actions) {
  70  |       expect(action.visible, `${width}px ${action.className} is visible`).toBe(true)
  71  |       expect(action.textFits, `${width}px ${action.className} text fits`).toBe(true)
  72  |       expect(action.right).toBeLessThanOrEqual(measurements.footer.right + 1)
  73  |     }
  74  |     expect(measurements.footer.scrollWidth).toBeLessThanOrEqual(measurements.footer.clientWidth + 1)
  75  |     if (width <= 390) {
  76  |       expect(measurements.actions.find(action => action.className === 'quote-action-save').width).toBeGreaterThan(measurements.footer.width * 0.75)
  77  |       expect(measurements.actions.find(action => action.className === 'quote-action-save-export').width).toBeGreaterThan(measurements.footer.width * 0.75)
  78  |       expect(Math.abs(measurements.actions[0].y - measurements.actions[1].y)).toBeLessThanOrEqual(2)
  79  |       expect(measurements.actions[2].y).toBeGreaterThan(measurements.actions[1].y)
  80  |       expect(measurements.actions[3].y).toBeGreaterThan(measurements.actions[2].y)
  81  |     }
  82  |     layouts.push(measurements)
  83  |     await page.screenshot({ path: path.join(evidenceDir, `chrome-quote-actions-${width}.png`) })
  84  |   }
  85  | 
  86  |   // Preview opens from the current draft and closing it preserves the selected line.
  87  |   await editor.getByRole('button', { name: '预览报价单', exact: true }).click()
  88  |   const preview = page.getByRole('dialog', { name: '报价单预览' })
  89  |   await expect(preview).toBeVisible()
  90  |   await expect(preview).toContainText('当前未保存内容')
  91  |   await preview.getByRole('button', { name: '关闭预览', exact: true }).click()
  92  |   await expect(editor.locator('.quote-line-row')).toHaveCount(1)
  93  | 
  94  |   // Save-only creates a quote without starting an export.
  95  |   const saveResponsePromise = page.waitForResponse(response =>
  96  |     new URL(response.url()).pathname === '/api/quotes/' && response.request().method() === 'POST')
  97  |   await editor.getByRole('button', { name: '保存报价', exact: true }).click()
  98  |   const saveResponse = await saveResponsePromise
  99  |   expect(saveResponse.status()).toBe(201)
  100 |   const savedQuote = await saveResponse.json()
  101 |   await expect(editor).toHaveCount(0)
  102 | 
  103 |   // Save-and-export remains a single action: create succeeds and an XLSX download follows.
  104 |   editor = await openEditor()
  105 |   await editor.locator('.sku-picker-options label').filter({ hasText: 'R1-UX-QA-SKU' }).locator('input[type="checkbox"]').check()
  106 |   const exportResponsePromise = page.waitForResponse(response =>
  107 |     new URL(response.url()).pathname === '/api/quotes/' && response.request().method() === 'POST')
  108 |   const downloadPromise = page.waitForEvent('download')
  109 |   await editor.getByRole('button', { name: '保存并导出 Excel', exact: true }).click()
  110 |   const exportResponse = await exportResponsePromise
  111 |   expect(exportResponse.status()).toBe(201)
  112 |   const exportedQuote = await exportResponse.json()
  113 |   const download = await downloadPromise
  114 |   expect(download.suggestedFilename().toLowerCase()).toContain('.xlsx')
  115 |   const downloadPath = path.join(process.env.ISOLATED_TEST_ROOT, download.suggestedFilename())
  116 |   await download.saveAs(downloadPath)
  117 |   const downloadBytes = (await fs.stat(downloadPath)).size
  118 |   await expect(editor).toHaveCount(0)
  119 | 
  120 |   await fs.writeFile(path.join(evidenceDir, 'browser-results.json'), JSON.stringify({
  121 |     browser: await page.evaluate(() => navigator.userAgent),
  122 |     layouts,
  123 |     preview: 'opened and closed; draft line remained',
  124 |     save: { status: saveResponse.status(), id: savedQuote.id, quote_no: savedQuote.quote_no },
  125 |     saveAndExport: { status: exportResponse.status(), id: exportedQuote.id, quote_no: exportedQuote.quote_no, filename: download.suggestedFilename(), downloadBytes },
```