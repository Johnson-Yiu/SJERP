# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: quote-editor-mobile-actions.spec.js >> quote editor actions stay readable at desktop and narrow widths and preserve preview/save/export
- Location: browser-tests\quote-editor-mobile-actions.spec.js:10:1

# Error details

```
Error: download.saveAs: canceled
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
          - strong [ref=f2e216]: "2"
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
          - option "全部客户"
          - option "报价操作验收客户" [selected]
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
            - cell "SJ20261104DE002 原始报价" [ref=f2e272]:
              - generic [ref=f2e278]:
                - strong [ref=f2e279]: SJ20261104DE002
                - generic [ref=f2e280]: 原始报价
            - cell "报价操作验收客户" [ref=f2e281]
            - cell "2026/11/05 03:00" [ref=f2e282]
            - cell "草稿" [ref=f2e283]
            - cell "1 项" [ref=f2e285]
            - cell "USD 12.50" [ref=f2e286]
            - cell [ref=f2e287]:
              - generic [ref=f2e288]:
                - button "查看 SJ20261104DE002" [ref=f2e289]
                - button "创建修订版 SJ20261104DE002" [ref=f2e293]
                - button "导出 SJ20261104DE002" [ref=f2e297]
          - row [ref=f2e301] [cursor=pointer]:
            - cell "SJ20261104DE001 原始报价" [ref=f2e302]:
              - generic [ref=f2e308]:
                - strong [ref=f2e309]: SJ20261104DE001
                - generic [ref=f2e310]: 原始报价
            - cell "报价操作验收客户" [ref=f2e311]
            - cell "2026/11/05 03:00" [ref=f2e312]
            - cell "草稿" [ref=f2e313]
            - cell "1 项" [ref=f2e315]
            - cell "USD 12.50" [ref=f2e316]
            - cell [ref=f2e317]:
              - generic [ref=f2e318]:
                - button "查看 SJ20261104DE001" [ref=f2e319]
                - button "创建修订版 SJ20261104DE001" [ref=f2e323]
                - button "导出 SJ20261104DE001" [ref=f2e327]
      - dialog "报价工作台" [ref=f2e332]:
        - generic [ref=f2e333]:
          - generic [ref=f2e335]:
            - button "关闭报价详情" [ref=f2e336] [cursor=pointer]
            - generic [ref=f2e340]: 报价工作台 · SJ20261104DE002
          - generic [ref=f2e341]:
            - generic [ref=f2e342]:
              - paragraph [ref=f2e343]: 报价操作验收客户 · 原始报价
              - heading "SJ20261104DE002" [level=2] [ref=f2e344]
              - text: 原始报价：SJ20261104DE002
            - generic [ref=f2e345]: 草稿
          - generic "报价状态操作" [ref=f2e346]:
            - button "标记为已发送" [ref=f2e347] [cursor=pointer]
            - button "标记为客户已接受" [ref=f2e348] [cursor=pointer]
            - button "标记为客户已拒绝" [ref=f2e349] [cursor=pointer]
          - generic [ref=f2e350]:
            - button "创建修订版" [ref=f2e351] [cursor=pointer]
            - button "预览 PI" [ref=f2e355] [cursor=pointer]
            - button "导出 Excel" [ref=f2e359] [cursor=pointer]
            - button "创建销售订单" [ref=f2e363] [cursor=pointer]
        - main [ref=f2e368]:
          - navigation "报价详情分页" [ref=f2e369]:
            - button "概览" [ref=f2e370] [cursor=pointer]
            - button "报价明细 (1)" [ref=f2e371] [cursor=pointer]
            - button "版本谱系 (1)" [ref=f2e372] [cursor=pointer]
            - button "订单 (0)" [ref=f2e373] [cursor=pointer]
            - button "重要备注 (0)" [ref=f2e374] [cursor=pointer]
            - button "操作日志 (0)" [ref=f2e375] [cursor=pointer]
          - generic [ref=f2e376]:
            - generic [ref=f2e377]:
              - heading "报价概览" [level=3] [ref=f2e378]
              - generic [ref=f2e379]:
                - generic [ref=f2e380]:
                  - generic [ref=f2e381]: 报价总额
                  - strong [ref=f2e382]: USD 12.50
                - generic [ref=f2e383]:
                  - generic [ref=f2e384]: 有效期至
                  - strong [ref=f2e385]: 2026-12-04
                - generic [ref=f2e386]:
                  - generic [ref=f2e387]: 商品明细
                  - strong [ref=f2e388]: 1 项
            - generic [ref=f2e389]:
              - heading "基础信息" [level=3] [ref=f2e390]
              - generic [ref=f2e391]:
                - term [ref=f2e392]: 报价日期
                - definition [ref=f2e393]: 2026-11-04
                - term [ref=f2e394]: 币种 / 汇率
                - definition [ref=f2e395]: USD / 7.2
                - term [ref=f2e396]: 收件人
                - definition [ref=f2e397]: 报价操作验收客户
                - term [ref=f2e398]: 条款备注
                - definition [ref=f2e399]: —
            - generic [ref=f2e400]:
              - generic [ref=f2e401]:
                - generic [ref=f2e402]:
                  - heading "修订摘要" [level=3] [ref=f2e403]
                  - paragraph [ref=f2e408]: 共 1 个版本，当前查看 原始报价。
                - button "查看修订历史" [ref=f2e409] [cursor=pointer]
              - article [ref=f2e411]:
                - generic [ref=f2e412]:
                  - strong [ref=f2e413]: SJ20261104DE002
                  - generic [ref=f2e414]: 原始报价
                  - generic [ref=f2e415]: 2026/11/05 03:00
                  - generic [ref=f2e416]: 草稿
                - generic [ref=f2e417]:
                  - text: USD 12.50
                  - generic [ref=f2e418]:
                    - button "预览 PI" [ref=f2e419] [cursor=pointer]
                    - button "查看详情" [disabled] [ref=f2e420] [cursor=pointer]
            - generic [ref=f2e421]:
              - heading "销售订单摘要" [level=3] [ref=f2e422]
              - paragraph [ref=f2e427]: 已生成 0 张销售订单。
              - button "查看关联销售订单" [ref=f2e428] [cursor=pointer]
      - generic [ref=f2e429]: 报价 SJ20261104DE002 已保存
```

# Test source

```ts
  16  |     if (new URL(response.url()).pathname.startsWith('/api/quotes/')) {
  17  |       apiResponses.push({ method: response.request().method(), path: new URL(response.url()).pathname, status: response.status() })
  18  |     }
  19  |   })
  20  | 
  21  |   async function openEditor() {
  22  |     await page.goto(`/quotes?create=1&customer=${fixture.customer}`)
  23  |     const editor = page.locator('form.quote-editor-modal')
  24  |     await expect(editor).toBeVisible()
  25  |     await expect(editor.locator('.quote-action-save-export')).toBeVisible()
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
  88  |   const preview = page.getByRole('dialog', { name: 'PI 预览' })
  89  |   await expect(preview).toBeVisible()
  90  |   await expect(preview).toContainText('当前内容尚未保存')
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
> 116 |   await download.saveAs(downloadPath)
      |                  ^ Error: download.saveAs: canceled
  117 |   const downloadBytes = (await fs.stat(downloadPath)).size
  118 |   await expect(editor).toHaveCount(0)
  119 | 
  120 |   await fs.writeFile(path.join(evidenceDir, 'browser-results.json'), JSON.stringify({
  121 |     browser: await page.evaluate(() => navigator.userAgent),
  122 |     layouts,
  123 |     preview: 'opened and closed; draft line remained',
  124 |     save: { status: saveResponse.status(), id: savedQuote.id, quote_no: savedQuote.quote_no },
  125 |     saveAndExport: { status: exportResponse.status(), id: exportedQuote.id, quote_no: exportedQuote.quote_no, filename: download.suggestedFilename(), downloadBytes },
  126 |     apiResponses,
  127 |   }, null, 2), 'utf8')
  128 | })
  129 | 
```