# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: prelaunch-p1-05-feedback-02.spec.js >> authenticated codex superuser imports XLSX and downloads the actual error CSV
- Location: browser-tests\prelaunch-p1-05-feedback-02.spec.js:103:1

# Error details

```
Error: locator.waitFor: Error: strict mode violation: getByRole('alert').filter({ hasText: '提交结果待核对' }) resolved to 2 elements:
    1) <div role="alert" data-v-345ef8a1="" class="result error-result">…</div> aka locator('div').filter({ hasText: /^网络连接失败，请检查网络后重试。 提交结果待核对，请保留原文件和预览再次确认原批次；离开页面不代表回滚。$/ })
    2) <p role="alert" class="stage" data-v-345ef8a1="">网络连接失败，请检查网络后重试。 提交结果待核对，请保留原文件和预览再次确认原批次；离开页面不代表…</p> aka locator('p').filter({ hasText: '网络连接失败，请检查网络后重试。 提交结果待核对，请保留原文件和预览再次确认原批次；离开页面不代表回滚。' })

Call log:
  - waiting for getByRole('alert').filter({ hasText: '提交结果待核对' }) to be visible

```

# Page snapshot

```yaml
- generic [ref=e1]:
  - generic [ref=e3]:
    - complementary [ref=e4]:
      - generic [ref=e5]:
        - generic [ref=e6]: S
        - generic [ref=e7]:
          - strong [ref=e8]: 森爵照明管理系统
          - text: 客户 · 销售 · 产品
      - navigation [ref=e9]:
        - generic [ref=e10]: 经营
        - link "经营概览" [ref=e11] [cursor=pointer]:
          - /url: /
        - link "报表中心" [ref=e18] [cursor=pointer]:
          - /url: /reports
        - link "历史订单分析" [ref=e25] [cursor=pointer]:
          - /url: /historical-orders
        - generic [ref=e31]: 客户
        - link "客户管理" [ref=e32] [cursor=pointer]:
          - /url: /customers
        - link "联系人" [ref=e39] [cursor=pointer]:
          - /url: /contacts
        - link "跟进记录" [ref=e45] [cursor=pointer]:
          - /url: /follow-ups
        - generic [ref=e49]: 销售
        - link "报价管理" [ref=e50] [cursor=pointer]:
          - /url: /quotes
        - link "订单管理" [ref=e55] [cursor=pointer]:
          - /url: /orders
        - generic [ref=e61]: 采购与库存
        - link "供应商管理" [ref=e62] [cursor=pointer]:
          - /url: /suppliers
        - link "采购管理" [ref=e69] [cursor=pointer]:
          - /url: /purchase-orders
        - link "库存" [ref=e75] [cursor=pointer]:
          - /url: /inventory
        - link "库存流水" [ref=e80] [cursor=pointer]:
          - /url: /inventory-movements
        - generic [ref=e85]: 产品资料
        - link "产品管理" [ref=e86] [cursor=pointer]:
          - /url: /products
        - link "SKU 管理" [ref=e92] [cursor=pointer]:
          - /url: /skus
        - link "产品分类" [ref=e104] [cursor=pointer]:
          - /url: /categories
        - link "产品参数" [ref=e110] [cursor=pointer]:
          - /url: /product-parameters
        - link "包装管理" [ref=e113] [cursor=pointer]:
          - /url: /sku-packaging
        - link "交易单位" [ref=e119] [cursor=pointer]:
          - /url: /sku-trade-units
        - link "产品证书" [ref=e131] [cursor=pointer]:
          - /url: /product-certificates
        - link "HS 编码维护" [ref=e136] [cursor=pointer]:
          - /url: /hs-codes
        - generic [ref=e139]: 财务与工具
        - link "财务概览" [ref=e140] [cursor=pointer]:
          - /url: /finance
        - link "应收计划" [ref=e146] [cursor=pointer]:
          - /url: /receivables
        - link "应付计划" [ref=e152] [cursor=pointer]:
          - /url: /payables
        - link "财务流水" [ref=e158] [cursor=pointer]:
          - /url: /transactions
        - link "银行资金记录" [ref=e164] [cursor=pointer]:
          - /url: /rmb-cash-events
        - link "账户余额与对账" [ref=e170] [cursor=pointer]:
          - /url: /finance-ledger
        - link "数据导入" [ref=e176] [cursor=pointer]:
          - /url: /import
        - link "历史资料预检" [ref=e181] [cursor=pointer]:
          - /url: /history-preflight
        - link "历史资料承接" [ref=e187] [cursor=pointer]:
          - /url: /history-takeover
        - generic [ref=e193]: 组织与系统
        - link "组织与权限" [ref=e194] [cursor=pointer]:
          - /url: /organization
      - generic [ref=e199]:
        - generic [ref=e200]: C
        - generic [ref=e202]:
          - strong [ref=e203]: 当前账号：codex
          - generic [ref=e204]: 超级管理员 · 全部功能与数据权限
        - button "退出登录" [ref=e205] [cursor=pointer]
    - main [ref=e206]:
      - generic [ref=e207]:
        - generic [ref=e208]:
          - text: Data onboarding
          - heading "数据导入" [level=1] [ref=e209]
        - generic [ref=e210]:
          - generic [ref=e211]: 11月14日周六
          - generic "codex" [ref=e212]: C
      - tablist "业务工作区" [ref=e214]:
        - generic [ref=e215]:
          - tab "数据导入" [selected] [ref=e216] [cursor=pointer]
          - button "关闭 数据导入" [ref=e217] [cursor=pointer]: ×
          - button "数据导入 标签操作" [ref=e218] [cursor=pointer]: ⋮
      - tabpanel "数据导入" [ref=e220]:
        - generic [ref=e221]:
          - generic [ref=e222]:
            - generic [ref=e223]:
              - heading "数据导入" [level=2] [ref=e224]
              - paragraph [ref=e225]: 上传文件并预览校验；确认后再写入业务数据。
            - link "历史资料预检与承接" [ref=e226] [cursor=pointer]:
              - /url: /history-takeover
          - tablist "导入类型" [ref=e227]:
            - tab "客户、产品与财务流水" [ref=e228] [cursor=pointer]
            - tab "销售订单" [selected] [ref=e229] [cursor=pointer]
          - generic [ref=e230]:
            - generic [ref=e231]:
              - status [ref=e232]: 有导入批次结果待核对：sales-order-import-input.xlsx。请重新选择对应原文件，按原预览凭证查询批次结果；不会创建新订单。
              - generic [ref=e233]:
                - generic [ref=e234]: "01"
                - generic [ref=e235]:
                  - heading "下载销售订单模板" [level=3] [ref=e236]
                  - paragraph [ref=e237]: 一行填写一条 SKU 明细。同一来源订单编号的多行会合并为一张销售订单草稿。
              - button "下载销售订单 XLSX 模板 包含来源订单编号、客户编号、订单日期、币种、SKU、交易单位、数量和单价" [ref=e238] [cursor=pointer]:
                - generic [ref=e242]:
                  - strong [ref=e243]: 下载销售订单 XLSX 模板
                  - generic [ref=e244]: 包含来源订单编号、客户编号、订单日期、币种、SKU、交易单位、数量和单价
              - generic [ref=e245]:
                - generic [ref=e246]: "02"
                - generic [ref=e247]:
                  - heading "上传并检查订单" [level=3] [ref=e248]
                  - paragraph [ref=e249]: 客户编号和 SKU 按系统编号匹配。每张订单的客户、日期、币种和汇率必须一致；预览不会写入业务数据，有明细错误时整单不导入。
              - generic [ref=e250] [cursor=pointer]:
                - strong [ref=e254]: sales-order-import-input.xlsx
                - generic [ref=e255]: 5.1 KB
              - button "预览并校验" [ref=e256] [cursor=pointer]
              - status [ref=e257]: 校验完成，可确认创建草稿
              - alert [ref=e258]: 网络连接失败，请检查网络后重试。 提交结果待核对，请保留原文件和预览再次确认原批次；离开页面不代表回滚。
              - generic [ref=e264]:
                - strong [ref=e265]: 共 3 条明细、2 张订单：1 张可导入，1 张待修正
                - paragraph [ref=e266]: 仅创建校验通过的整单；含错误的订单会整单跳过。
                - table [ref=e268]:
                  - rowgroup [ref=e269]:
                    - row [ref=e270]:
                      - columnheader "来源订单编号" [ref=e271]
                      - columnheader "客户（编号）" [ref=e272]
                      - columnheader "明细数" [ref=e273]
                      - columnheader "金额" [ref=e274]
                      - columnheader "状态" [ref=e275]
                  - rowgroup [ref=e276]:
                    - row [ref=e277]:
                      - cell "UAT-EXT-ORDER-001" [ref=e278]
                      - cell "导入验收合成客户（UAT-IMP-C001）" [ref=e279]
                      - cell "2" [ref=e280]
                      - cell "CNY 96.00" [ref=e281]
                      - cell "待导入" [ref=e282]
                    - row [ref=e283]:
                      - cell "UAT-EXT-ORDER-BAD" [ref=e284]
                      - cell "UAT-IMP-C001" [ref=e285]
                      - cell "1" [ref=e286]
                      - cell "CNY 0.00" [ref=e287]
                      - cell "待修正" [ref=e288]
                - generic [ref=e289]:
                  - paragraph [ref=e290]: 表格行号按 Excel 中的实际行号显示。请按错误原因修正原文件后重新预览。
                  - table [ref=e291]:
                    - rowgroup [ref=e292]:
                      - row [ref=e293]:
                        - columnheader "表格行号" [ref=e294]
                        - columnheader "来源订单编号" [ref=e295]
                        - columnheader "错误原因" [ref=e296]
                    - rowgroup [ref=e297]:
                      - row [ref=e298]:
                        - cell "4" [ref=e299]
                        - cell "UAT-EXT-ORDER-BAD" [ref=e300]
                        - cell "找不到 SKU：UAT-UNKNOWN-SKU。" [ref=e301]
                - button "下载导入结果 CSV" [ref=e302] [cursor=pointer]
                - button "下载错误清单 CSV" [ref=e303] [cursor=pointer]
                - alert [ref=e304]: 网络连接失败，请检查网络后重试。 提交结果待核对，请保留原文件和预览再次确认原批次；离开页面不代表回滚。
                - button "确认导入 1 张草稿" [ref=e305] [cursor=pointer]
            - complementary [ref=e306]:
              - heading "销售订单规则" [level=3] [ref=e307]
              - list [ref=e308]:
                - listitem [ref=e309]:
                  - generic [ref=e310]: "1"
                  - generic [ref=e311]:
                    - strong [ref=e312]: 按编号匹配
                    - generic [ref=e313]: 客户编号、SKU 和交易单位
                - listitem [ref=e314]:
                  - generic [ref=e315]: "2"
                  - generic [ref=e316]:
                    - strong [ref=e317]: 整单校验
                    - generic [ref=e318]: 检查表头一致、金额和交易单位
                - listitem [ref=e319]:
                  - generic [ref=e320]: "3"
                  - generic [ref=e321]:
                    - strong [ref=e322]: 确认后建草稿
                    - generic [ref=e323]: 使用订单管理中的原有流程确认
              - generic [ref=e324]:
                - strong [ref=e325]: 旧订单请走历史流程
                - paragraph [ref=e326]: 已结清、已收款、已发货或需要接续的订单，请在历史资料承接页提交；系统会先预检，再进入申请审核。
                - link "打开历史资料承接" [ref=e327] [cursor=pointer]:
                  - /url: /history-takeover
              - generic [ref=e328]:
                - strong [ref=e329]: 导入范围
                - paragraph [ref=e330]: 不会确认订单、占库存、生成应收计划或登记发货。重复来源订单编号会拒绝导入，内容变更也不会覆盖已有订单。
  - dialog [ref=e332]:
    - banner [ref=e333]:
      - heading "操作正在提交" [level=2] [ref=e334]
    - paragraph [ref=e336]: 请等待当前操作完成后再关闭。
    - contentinfo [ref=e337]:
      - button "知道了" [active] [ref=e338] [cursor=pointer]
```

# Test source

```ts
  70  |   })
  71  |   await drawer.getByRole('button', { name: '创建 采购草稿' }).click()
  72  |   await expect(drawer.getByRole('button', { name: '创建中…' })).toBeDisabled()
  73  |   await capture('procurement-pending')
  74  |   // A pending write must not lose its result by closing the drawer.
  75  |   try {
  76  |     await drawer.getByRole('button', { name: '关闭', exact: true }).click()
  77  |     await expect(drawer).toBeVisible()
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
> 170 |   await page.getByRole('alert').filter({hasText:'提交结果待核对'}).waitFor()
      |                                                             ^ Error: locator.waitFor: Error: strict mode violation: getByRole('alert').filter({ hasText: '提交结果待核对' }) resolved to 2 elements:
  171 |   await capture('import-lost-response')
  172 |   await page.unroute('**/api/import/orders/execute/')
  173 |   await page.reload()
  174 |   await page.getByRole('tab', {name:'销售订单',exact:true}).click()
  175 |   await page.locator('input[type="file"][accept*=".xlsx"]').setInputFiles(workbookPath)
  176 |   await expect(page.getByRole('alert').filter({ hasText: '已恢复待核对导入批次' })).toBeVisible()
  177 |   const executeResponsePromise = page.waitForResponse(response => new URL(response.url()).pathname === '/api/import/orders/execute/' && response.request().method() === 'POST')
  178 |   await page.getByRole('button', {name:'确认导入 1 张草稿',exact:true}).click()
  179 |   await page.getByTestId('dialog-confirm').click()
  180 |   const executeResponse = await executeResponsePromise
  181 |   expect(executeResponse.status()).toBe(200)
  182 |   const result = await executeResponse.json()
  183 |   expect(result.batch_id).toBe(savedResult.batch_id)
  184 |   expect(result).toMatchObject({ created_orders: 1, failed_orders: 1, total_orders: 2 })
  185 |   expect(result.orders).toHaveLength(1)
  186 |   expect(result.orders[0]).toMatchObject({ source_order_no: fixture.valid_source_order, status: 'draft', line_count: 2 })
  187 |   await page.getByText('已创建 1 张草稿，1 张未创建', { exact: true }).waitFor()
  188 | 
  189 |   const errorDownloadPromise = page.waitForEvent('download')
  190 |   await page.getByRole('button', { name: '下载错误清单 CSV', exact: true }).click()
  191 |   const errorDownload = await errorDownloadPromise
  192 |   expect(errorDownload.suggestedFilename()).toBe('sales-order-import-errors.csv')
  193 |   const csvPath = path.join(evidenceDir, errorDownload.suggestedFilename())
  194 |   await errorDownload.saveAs(csvPath)
  195 |   const csvBytes = await readFile(csvPath)
  196 |   const csvText = csvBytes.toString('utf8')
  197 |   expect(csvText.startsWith('\ufeff')).toBe(true)
  198 |   expect(csvText).toContain(fixture.invalid_source_order)
  199 |   expect(csvText).toContain(fixture.invalid_sku)
  200 |   expect(csvText).toContain('找不到 SKU')
  201 | 
  202 |   const resultLookup = await page.request.get(`/api/import/orders/results/${result.batch_id}/`)
  203 |   expect(resultLookup.status()).toBe(200)
  204 |   expect(await resultLookup.json()).toEqual(result)
  205 | 
  206 |   await capture('import-idempotent-success')
  207 |   await writeFile(path.join(evidenceDir, 'p1-05-result.json'), JSON.stringify({
  208 |     source: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
  209 |     result, retryStatus: executeResponse.status(), originalBatch: savedResult.batch_id,
  210 |     lookupStatus: resultLookup.status(), errorCsvContainsInvalidSku: csvText.includes(fixture.invalid_sku),
  211 |   }, null, 2))
  212 | })
  213 | 
```