Generated readable copy; exact original bytes: generated-failure-context-raw.zip

# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: cash-events-p2b.spec.js >> expired local draft is removed during page initialization and sensitive evidence is not persisted
- Location: browser-tests\cash-events-p2b.spec.js:153:1

# Error details

```
Error: expect(received).toBeNull()

Received: "{\"saved_at\":1793693941713,\"form\":{\"request_key\":\"EXPIRED-REQUEST\",\"evidence_sha256\":\"secret-hash\",\"evidence_note\":\"private note\"},\"allocations\":[]}"
```

# Page snapshot

```yaml
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
      - link "人民币资金" [ref=e164] [cursor=pointer]:
        - /url: /rmb-cash-events
      - link "数据导入" [ref=e170] [cursor=pointer]:
        - /url: /import
      - generic [ref=e175]: 组织与系统
      - link "组织与权限" [ref=e176] [cursor=pointer]:
        - /url: /organization
    - generic [ref=e181]:
      - generic [ref=e182]: —
      - generic [ref=e184]:
        - strong [ref=e185]: 开发身份：
        - generic [ref=e186]: · 全部功能与数据权限
  - main [ref=e187]:
    - generic [ref=e188]:
      - generic [ref=e189]:
        - text: Bank cash facts
        - heading "人民币资金" [level=1] [ref=e190]
      - generic [ref=e191]:
        - generic [ref=e192]: 11月4日周三
        - generic [ref=e193]: —
    - generic [ref=e195]:
      - generic [ref=e196]:
        - generic [ref=e197]:
          - paragraph [ref=e198]: 人民币实际资金
          - heading "银行资金记录" [level=2] [ref=e199]
          - paragraph [ref=e200]: 登记系统中的人民币银行资金事件；只有已确认的事件才纳入银行实际人民币资金汇总。结汇不新增客户收款，也不改变应收核销。
        - generic [ref=e201]:
          - link "查看财务流水" [ref=e202] [cursor=pointer]:
            - /url: /transactions
          - button "新建资金事件" [ref=e203] [cursor=pointer]
      - paragraph [ref=e204]:
        - strong [ref=e205]: 口径：
        - text: 只有人工核实银行凭证的事件可以确认。已确认仅表示本系统已登记且确认的银行事实，不代表公司全部银行余额；待确认资金不是已实际到账。参考折算只用于对照，不代表银行实际到账；手续费按银行净额说明，不重复扣除。
      - form "人民币资金筛选" [ref=e206]:
        - generic [ref=e207]:
          - text: 状态
          - combobox "状态" [ref=e208]:
            - option "全部状态" [selected]
            - option "待确认"
            - option "已确认"
            - option "已放弃"
        - generic [ref=e209]:
          - text: 搜索
          - searchbox "搜索" [ref=e210]
        - button "刷新" [ref=e211] [cursor=pointer]
      - paragraph [ref=e212]: 列表同时包含待确认、已确认和已放弃记录；只有已确认记录计入银行实际人民币资金。本页“银行日期”指银行实际入账 / 扣款日期；流水发生日期请在财务流水页查看。退款、反向更正和历史资金归属不会在本页自动处理，请按原始凭证核对。
      - status [ref=e213]: 正在加载…
```

# Test source

```ts
  68  |   await expect(page.locator('.preview-box')).toBeVisible()
  69  |   expect(previewCalls).toBe(1)
  70  |   await page.getByLabel('银行净额（CNY）').fill('706.00')
  71  |   await expect(page.locator('.preview-box')).toHaveCount(0)
  72  |   await expect(page.getByText('旧预览已失效')).toBeVisible()
  73  |   await expect(page.getByRole('button', { name: '后端预览' })).toBeVisible()
  74  | })
  75  |
  76  | test('refresh restores the stable request key and draft inputs without registering', async ({ page }) => {
  77  |   await page.route('**/api/**', async route => {
  78  |     const path = new URL(route.request().url()).pathname
  79  |     if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
  80  |     if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [] } })
  81  |     return route.fulfill({ json: [] })
  82  |   })
  83  |   await page.goto('/rmb-cash-events')
  84  |   await page.getByRole('button', { name: '新建资金事件' }).click()
  85  |   const requestKey = await page.getByLabel('稳定请求键').inputValue()
  86  |   await page.getByLabel('银行净额（CNY）').fill('705.00')
  87  |   await page.reload()
  88  |   await page.getByRole('button', { name: '新建资金事件' }).click()
  89  |   await expect(page.getByLabel('稳定请求键')).toHaveValue(requestKey)
  90  |   await expect(page.getByLabel('银行净额（CNY）')).toHaveValue('705')
  91  | })
  92  |
  93  | test('restored draft remains protected and explicit abandon clears only after confirmation', async ({ page }) => {
  94  |   await page.route('**/api/**', async route => {
  95  |     const path = new URL(route.request().url()).pathname
  96  |     if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
  97  |     if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [] } })
  98  |     return route.fulfill({ json: [] })
  99  |   })
  100 |   await page.goto('/rmb-cash-events')
  101 |   await page.getByRole('button', { name: '新建资金事件' }).click()
  102 |   const requestKey = await page.getByLabel('稳定请求键').inputValue()
  103 |   await page.getByLabel('银行净额（CNY）').fill('705.00')
  104 |   await page.reload()
  105 |   await page.getByRole('button', { name: '新建资金事件' }).click()
  106 |   await expect(page.getByText('已恢复未完成草稿')).toBeVisible()
  107 |   await page.getByRole('button', { name: '取消', exact: true }).click()
  108 |   await expect(page.getByRole('heading', { name: '未保存修改', exact: true })).toBeVisible()
  109 |   await page.getByRole('button', { name: '继续编辑', exact: true }).click()
  110 |   await expect(page.getByLabel('稳定请求键')).toHaveValue(requestKey)
  111 |   await expect(page.getByLabel('银行净额（CNY）')).toHaveValue('705')
  112 |   await page.getByRole('button', { name: '取消', exact: true }).click()
  113 |   await page.getByRole('button', { name: '放弃修改', exact: true }).click()
  114 |   await expect(page.getByRole('heading', { name: '新建人民币资金事件', exact: true })).toHaveCount(0)
  115 |   await page.getByRole('button', { name: '新建资金事件' }).click()
  116 |   await expect(page.getByLabel('稳定请求键')).not.toHaveValue(requestKey)
  117 | })
  118 |
  119 | test('changing a 30 allocation to 50 clears verification and requires a fresh preview', async ({ page }) => {
  120 |   let previewCalls = 0
  121 |   await page.route('**/api/**', async route => {
  122 |     const path = new URL(route.request().url()).pathname
  123 |     if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
  124 |     if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [{ id: 1, transaction_no: 'P2B-30-50-SOURCE', currency: 'USD', direction: 'income', amount: '100.00', remaining_candidate_amount: '100.00', blocked_reason: null }] } })
  125 |     if (path === '/api/rmb-cash-events/preview/') { previewCalls += 1; return route.fulfill({ json: { source_total: '30.00', bank_net_amount: '213.00', confirmed: false, sources: [] } }) }
  126 |     return route.fulfill({ json: [] })
  127 |   })
  128 |   await page.goto('/rmb-cash-events')
  129 |   await page.getByRole('button', { name: '新建资金事件' }).click()
  130 |   await page.getByLabel('银行净额（CNY）').fill('213.00')
  131 |   await page.getByLabel('来源银行账户标识').fill('SYNTH-FX-01')
  132 |   await page.getByLabel('人民币账户标识').fill('SYNTH-CNY-01')
  133 |   await page.getByLabel('银行参考号').fill('P2B-30-50')
  134 |   await page.getByRole('button', { name: '选择', exact: true }).click()
  135 |   await page.locator('.allocation-table input[type="number"]').fill('30')
  136 |   await page.locator('.verification-toggle input').check()
  137 |   await page.getByRole('button', { name: '后端预览' }).click()
  138 |   await expect(page.locator('.preview-box')).toBeVisible()
  139 |   expect(previewCalls).toBe(1)
  140 |   await page.locator('.allocation-table input[type="number"]').fill('50')
  141 |   await expect(page.locator('.verification-toggle input')).not.toBeChecked()
  142 |   await expect(page.locator('.preview-box')).toHaveCount(0)
  143 |   await expect(page.getByText('旧预览已失效')).toBeVisible()
  144 |   await page.getByRole('button', { name: '后端预览' }).click()
  145 |   await expect(page.getByRole('alert')).toHaveText('请逐条核实来源流水后再预览。')
  146 |   expect(previewCalls).toBe(1)
  147 |   await page.locator('.verification-toggle input').check()
  148 |   await page.getByRole('button', { name: '后端预览' }).click()
  149 |   await expect(page.locator('.preview-box')).toBeVisible()
  150 |   expect(previewCalls).toBe(2)
  151 | })
  152 |
  153 | test('expired local draft is removed during page initialization and sensitive evidence is not persisted', async ({ page }) => {
  154 |   await page.addInitScript(() => {
  155 |     localStorage.setItem('sunjack:r1-fin-p2-b:cash-event-draft:v1', JSON.stringify({
  156 |       saved_at: Date.now() - 25 * 60 * 60 * 1000,
  157 |       form: { request_key: 'EXPIRED-REQUEST', evidence_sha256: 'secret-hash', evidence_note: 'private note' },
  158 |       allocations: [],
  159 |     }))
  160 |   })
  161 |   await page.route('**/api/**', async route => {
  162 |     const path = new URL(route.request().url()).pathname
  163 |     if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
  164 |     if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [] } })
  165 |     return route.fulfill({ json: [] })
  166 |   })
  167 |   await page.goto('/rmb-cash-events')
> 168 |   expect(await page.evaluate(() => localStorage.getItem('sunjack:r1-fin-p2-b:cash-event-draft:v1'))).toBeNull()
      |                                                                                                      ^ Error: expect(received).toBeNull()
  169 |   await page.getByRole('button', { name: '新建资金事件' }).click()
  170 |   await page.getByLabel('银行净额（CNY）').fill('705.00')
  171 |   await expect.poll(() => page.evaluate(() => localStorage.getItem('sunjack:r1-fin-p2-b:cash-event-draft:v1'))).toContain('request_key')
  172 |   const draft = JSON.parse(await page.evaluate(() => localStorage.getItem('sunjack:r1-fin-p2-b:cash-event-draft:v1')))
  173 |   expect(draft.form).not.toHaveProperty('evidence_sha256')
  174 |   expect(draft.form).not.toHaveProperty('evidence_note')
  175 | })
  176 |
  177 | test('legacy draft is sanitized immediately when restored', async ({ page }) => {
  178 |   await page.addInitScript(() => {
  179 |     localStorage.setItem('sunjack:r1-fin-p2-b:cash-event-draft:v1', JSON.stringify({
  180 |       version: 1,
  181 |       saved_at: Date.now(),
  182 |       form: {
  183 |         request_key: 'LEGACY-REQUEST', event_no: 'LEGACY-EVENT', bank_net_amount: '705.00',
  184 |         evidence_reference: 'legacy-secret-voucher', evidence_sha256: 'b'.repeat(64), evidence_note: 'legacy private note',
  185 |       },
  186 |       allocations: [],
  187 |     }))
  188 |   })
  189 |   await page.route('**/api/**', async route => {
  190 |     const path = new URL(route.request().url()).pathname
  191 |     if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
  192 |     if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [] } })
  193 |     return route.fulfill({ json: [] })
  194 |   })
  195 |   await page.goto('/rmb-cash-events')
  196 |   await page.getByRole('button', { name: '新建资金事件' }).click()
  197 |   await expect(page.getByText('已恢复未完成草稿')).toBeVisible()
  198 |   const draft = JSON.parse(await page.evaluate(() => localStorage.getItem('sunjack:r1-fin-p2-b:cash-event-draft:v1')))
  199 |   expect(draft.version).toBe(2)
  200 |   expect(draft.form).not.toHaveProperty('evidence_reference')
  201 |   expect(draft.form).not.toHaveProperty('evidence_sha256')
  202 |   expect(draft.form).not.toHaveProperty('evidence_note')
  203 |   await expect(page.getByLabel('凭证引用')).toHaveValue('')
  204 |   await expect(page.getByText('凭证资料未保存在本地')).toBeVisible()
  205 | })
  206 |
  207 | test('stale source responses cannot overwrite the current currency', async ({ page }) => {
  208 |   await page.route('**/api/**', async route => {
  209 |     const request = route.request()
  210 |     const path = new URL(request.url()).pathname
  211 |     if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
  212 |     if (path === '/api/rmb-cash-events/sources/') {
  213 |       const currency = new URL(request.url()).searchParams.get('currency')
  214 |       if (currency === 'USD') {
  215 |         await new Promise(resolve => setTimeout(resolve, 250))
  216 |         return route.fulfill({ json: { results: [{ id: 1, transaction_no: 'STALE-USD', currency: 'USD', direction: 'income', amount: '100.00', remaining_candidate_amount: '100.00', blocked_reason: null }] } })
  217 |       }
  218 |       return route.fulfill({ json: { results: [{ id: 2, transaction_no: 'CURRENT-CNY', currency: 'CNY', direction: 'income', amount: '100.00', remaining_candidate_amount: '100.00', blocked_reason: null }] } })
  219 |     }
  220 |     return route.fulfill({ json: [] })
  221 |   })
  222 |   await page.goto('/rmb-cash-events')
  223 |   await page.getByRole('button', { name: '新建资金事件' }).click()
  224 |   await page.locator('.cash-dialog select').nth(0).selectOption('cny_direct')
  225 |   await expect(page.locator('.source-option')).toContainText('CURRENT-CNY')
  226 |   await page.waitForTimeout(350)
  227 |   await expect(page.locator('.source-option')).not.toContainText('STALE-USD')
  228 | })
  229 |
```
