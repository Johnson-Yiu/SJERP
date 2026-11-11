# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-final-state-customer-contact-03.spec.js >> customer creation selects an employee and preserves nested contacts after a rejected save
- Location: browser-tests/ui-final-state-customer-contact-03.spec.js:9:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('dialog', { name: '新建客户' }).getByRole('alert').filter({ hasText: '负责人资料加载失败' })
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('dialog', { name: '新建客户' }).getByRole('alert').filter({ hasText: '负责人资料加载失败' }) with timeout 30000ms
  - waiting for getByRole('dialog', { name: '新建客户' }).getByRole('alert').filter({ hasText: '负责人资料加载失败' })

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
  - text: 客户资料
  - heading "客户管理" [level=1]
  - text: 11月11日周三 C
  - tablist "业务工作区":
    - tab "客户管理"
    - button "关闭 客户管理": ×
    - button "客户管理 标签操作": ⋮
    - tab "客户管理 · 新建 1" [selected]
    - button "关闭 客户管理 · 新建 1": ×
    - button "客户管理 · 新建 1 标签操作": ⋮
  - tabpanel "客户管理 · 新建 1":
    - paragraph: 维护客户资料和负责人。客户阶段会随报价和订单自动更新。
    - button "新建客户"
    - region "页面小计":
      - article:
        - text: 客户总数
        - strong: "2"
        - text: 全部客户档案
      - article:
        - text: 正式客户
        - strong: "0"
        - text: 已有正式订单
      - article:
        - text: 待开发
        - strong: "2"
        - text: 尚未成交
      - article:
        - text: 累计销售额
        - strong: ¥ 0.00
        - text: 当前列表累计
    - link "新品提醒":
      - /url: /new-product-reminders?tag=%E6%96%B0%E5%93%81%E6%8F%90%E9%86%92
    - text: 搜索
    - textbox "搜索客户":
      - /placeholder: 名称、编号、国家/地区或负责人
    - text: 负责人
    - combobox "按负责人筛选客户":
      - option "全部负责人" [selected]
      - option "合成负责人 · 合成业务部"
    - text: 国家/地区
    - combobox "按国家/地区筛选客户":
      - option "全部国家/地区" [selected]
      - option "United States / US"
    - text: 状态
    - combobox "按客户状态筛选":
      - option "全部状态" [selected]
      - option "线索"
      - option "已联系"
      - option "商机"
      - option "正式客户"
      - option "返单客户"
    - button "重置"
    - button "刷新"
    - table:
      - rowgroup:
        - row "客户名称 客户编号 状态 国家/地区 业务区域 负责人 下次跟进 订单数 累计销售额 操作":
          - columnheader "客户名称"
          - columnheader "客户编号"
          - columnheader "状态"
          - columnheader "国家/地区"
          - columnheader "业务区域"
          - columnheader "负责人"
          - columnheader "下次跟进"
          - columnheader "订单数"
          - columnheader "累计销售额"
          - columnheader "操作"
      - rowgroup:
        - row "合成客户联系人分支-1366-100 202611110000 线索 — — 合成负责人 — 0 ¥ 0.00 新品提醒 查看详情 编辑 删除":
          - cell "合成客户联系人分支-1366-100"
          - cell "202611110000"
          - cell "线索"
          - cell "—"
          - cell "—"
          - cell "合成负责人"
          - cell "—"
          - cell "0"
          - cell "¥ 0.00"
          - cell "新品提醒 查看详情 编辑 删除":
            - link "新品提醒":
              - /url: /new-product-reminders?customer=2
            - button "查看详情"
            - button "编辑"
            - button "删除"
        - row "合成采购成本归属客户 EVID-C001 线索 United States / US — — — 0 ¥ 0.00 新品提醒 查看详情 编辑 删除":
          - cell "合成采购成本归属客户"
          - cell "EVID-C001"
          - cell "线索"
          - cell "United States / US"
          - cell "—"
          - cell "—"
          - cell "—"
          - cell "0"
          - cell "¥ 0.00"
          - cell "新品提醒 查看详情 编辑 删除":
            - link "新品提醒":
              - /url: /new-product-reminders?customer=1
            - button "查看详情"
            - button "编辑"
            - button "删除"
    - dialog "新建客户":
      - heading "新建客户" [level=3]
      - button
      - text: 客户名称
      - emphasis: "*"
      - textbox "客户名称":
        - /placeholder: 输入客户名称
      - text: 客户编号
      - emphasis: "*"
      - textbox "客户编号": "202611110001"
      - text: 国家/地区
      - textbox "国家/地区":
        - /placeholder: 搜索名称、中文或代码后选择
      - paragraph: 请选择标准英文名称 / 两位代码；历史文本需人工确认。
      - text: 业务区域
      - textbox "业务区域"
      - text: 负责人
      - combobox:
        - option "请选择" [selected]
        - option "合成负责人 · 合成业务部"
      - text: 客户来源
      - textbox "选择或输入"
      - text: 联系人信息
      - paragraph: 至少登记一位联系人，可指定默认联系人。
      - text: 1 位
      - strong: 联系人 1
      - checkbox "默认联系人" [checked]
      - text: 默认联系人 姓名
      - emphasis: "*"
      - textbox
      - text: 职位
      - textbox
      - text: 邮箱
      - textbox
      - text: 电话
      - textbox
      - text: WhatsApp
      - textbox
      - text: 备注
      - textbox
      - button "新增联系人"
      - heading "补充信息" [level=4]
      - text: 网站
      - textbox "网站"
      - text: 地址
      - textbox "地址"
      - text: 备注
      - textbox "备注"
      - button "取消"
      - button "保存客户"
```

# Test source

```ts
  1   | import { execFileSync } from 'node:child_process'
  2   | import { mkdir, readFile, writeFile } from 'node:fs/promises'
  3   | import path from 'node:path'
  4   | import { fileURLToPath } from 'node:url'
  5   | import { chromium, expect as playwrightExpect, test } from '@playwright/test'
  6   |
  7   | const expect = playwrightExpect.configure({ timeout: 30000 })
  8   |
  9   | test('customer creation selects an employee and preserves nested contacts after a rejected save', async ({ baseURL }) => {
  10  |   test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
  11  |     'Requires a dedicated seeded database; run this spec through the isolated runner.')
  12  |   test.setTimeout(2400000)
  13  |   const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  14  |   const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-customer-contact')
  15  |   await mkdir(output, { recursive: true })
  16  |   const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-final-state-closeout-03/seed.py', import.meta.url))
  17  |   const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
  18  |     cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, CLOSEOUT_CUSTOMER_CONTACT: '1' },
  19  |   }))
  20  |   const root = process.env.ISOLATED_TEST_ROOT
  21  |   const context = await chromium.launchPersistentContext(path.join(root, 'customer-contact-chrome'), {
  22  |     channel: 'chrome', viewport: { width: 390, height: 844 },
  23  |   })
  24  |   const states = []
  25  |   let browser
  26  |   let failure
  27  |   const save = () => writeFile(path.join(output, 'run.json'), JSON.stringify({ source, browser, states, failure }, null, 2) + '\n')
  28  |   try {
  29  |     const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
  30  |     await context.addCookies(auth.cookies)
  31  |     const settings = context.pages()[0]
  32  |     const page = await context.newPage()
  33  |     page.setDefaultTimeout(90000)
  34  |     const cdp = await context.newCDPSession(page)
  35  |     browser = (await cdp.send('Browser.getVersion')).product
  36  |     expect(browser).toMatch(/^Chrome\//)
  37  |     await settings.goto('chrome://settings/appearance', { waitUntil: 'commit', timeout: 240000 })
  38  |     const zoomControl = settings.locator('settings-appearance-page select').filter({ has: settings.locator('option[value="1.25"]') })
  39  |     let zoom = 1.25
  40  |     await zoomControl.selectOption(String(zoom), { timeout: 180000 })
  41  |     const go = route => page.goto(new URL(route, baseURL).href, { waitUntil: 'commit', timeout: 240000 })
  42  |
  43  |     for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
  44  |       for (const scale of [1, 1.25]) {
  45  |         zoom = scale
  46  |         await zoomControl.selectOption(String(zoom))
  47  |         await page.setViewportSize({ width, height })
  48  |         const capture = async id => {
  49  |           expect(await page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
  50  |           const png = id + '-' + width + '-' + zoom * 100 + '.png'
  51  |           const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
  52  |           await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
  53  |           states.push({ id, width, height, zoom, png })
  54  |           await save()
  55  |         }
  56  |         await go('/customers')
  57  |         const ownerEndpoint = url => url.pathname === '/api/customers/owner-options/'
  58  |         await page.route(ownerEndpoint, route => route.fulfill({ status: 400, json: { detail: '暂时无法读取人员资料' } }))
  59  |         await page.getByRole('button', { name: '新建客户', exact: true }).click()
  60  |         const editor = page.getByRole('dialog', { name: '新建客户' })
  61  |         const ownerError = editor.getByRole('alert').filter({ hasText: '负责人资料加载失败' })
> 62  |         await expect(ownerError).toBeVisible()
      |                                  ^ Error: expect(locator).toBeVisible() failed
  63  |         await ownerError.scrollIntoViewIfNeeded()
  64  |         await capture('customer-owner-options-failed')
  65  |         await page.unroute(ownerEndpoint)
  66  |         await ownerError.getByRole('button', { name: '重新加载', exact: true }).click()
  67  |         await expect(ownerError).toHaveCount(0)
  68  |         const employee = editor.locator('.field').filter({ has: page.getByText('负责人', { exact: true }) }).locator('select')
  69  |         const name = '合成客户联系人分支-' + width + '-' + zoom * 100
  70  |         const contactName = '合成采购联系人'
  71  |         await editor.getByLabel('客户名称', { exact: true }).fill(name)
  72  |         await expect(employee.locator('option', { hasText: '合成负责人 · 合成业务部' })).toHaveCount(1)
  73  |         await employee.selectOption(String(fixture.owner))
  74  |         await editor.getByRole('button', { name: '新增联系人' }).click()
  75  |         await editor.locator('.contact-create-card').first().locator('input').nth(1).fill('合成原联系人')
  76  |         const addedContact = editor.locator('.contact-create-card').last().locator('.contact-fields input').first()
  77  |         await addedContact.fill(contactName)
  78  |         const submit = editor.getByRole('button', { name: '保存客户', exact: true })
  79  |         const customerWrite = response => new URL(response.url()).pathname === '/api/customers/' && response.request().method() === 'POST'
  80  |         let release
  81  |         const gate = new Promise(resolve => { release = resolve })
  82  |         const customerEndpoint = url => url.pathname === '/api/customers/'
  83  |         await page.route(customerEndpoint, async route => {
  84  |           if (route.request().method() !== 'POST') return route.continue()
  85  |           await gate
  86  |           await route.fulfill({ status: 400, json: { detail: '合成校验失败，请重试' } })
  87  |         })
  88  |         const rejected = page.waitForResponse(customerWrite)
  89  |         try {
  90  |           await submit.click()
  91  |           const pending = editor.getByRole('button', { name: '保存中…', exact: true })
  92  |           await expect(pending).toBeDisabled()
  93  |           await pending.scrollIntoViewIfNeeded()
  94  |           await capture('customer-create-pending')
  95  |         } finally { release() }
  96  |         expect((await rejected).status()).toBe(400)
  97  |         await page.unroute(customerEndpoint)
  98  |         await expect(employee).toHaveValue(String(fixture.owner))
  99  |         await expect(addedContact).toHaveValue(contactName)
  100 |         await expect(submit).toBeEnabled()
  101 |         const created = page.waitForResponse(customerWrite)
  102 |         await submit.click()
  103 |         const response = await created
  104 |         expect(response.status(), await response.text()).toBe(201)
  105 |         const { id } = await response.json()
  106 |         await expect(editor).toHaveCount(0)
  107 |         await go('/customers?detail=' + id + '&tab=contacts')
  108 |         const detail = page.getByRole('dialog', { name: '客户详情' })
  109 |         await expect(detail.getByText(/负责人：合成负责人/)).toBeVisible()
  110 |         const contact = detail.getByText(contactName, { exact: true }).first()
  111 |         await expect(contact).toBeVisible()
  112 |         await contact.scrollIntoViewIfNeeded()
  113 |         await capture('customer-owner-and-contact-readback')
  114 |         await detail.getByRole('button', { name: '新增联系人', exact: true }).click()
  115 |         const related = page.locator('form.related-create-modal').filter({ has: page.getByRole('heading', { name: '新增联系人', exact: true }) })
  116 |         const contactField = label => related.locator('.field').filter({ has: page.locator('label').filter({ hasText: label }) })
  117 |         const relatedCustomer = contactField('所属客户').locator('select')
  118 |         await expect(relatedCustomer).toHaveValue(String(id))
  119 |         await expect(relatedCustomer).toBeDisabled()
  120 |         const nestedName = '合成详情新增联系人'
  121 |         await contactField('姓名').locator('input').fill(nestedName)
  122 |         const nestedResponse = page.waitForResponse(r => new URL(r.url()).pathname === '/api/contacts/' && r.request().method() === 'POST')
  123 |         await related.getByRole('button', { name: '保存', exact: true }).click()
  124 |         const nested = await nestedResponse
  125 |         expect(nested.status(), await nested.text()).toBe(201)
  126 |         expect((await nested.json()).customer).toBe(id)
  127 |         await expect(related).toHaveCount(0)
  128 |         const returnedContact = detail.getByText(nestedName, { exact: true }).first()
  129 |         await expect(returnedContact).toBeVisible()
  130 |         await expect(async () => { await returnedContact.scrollIntoViewIfNeeded(); await expect(returnedContact).toBeInViewport({ timeout: 2000 }) }).toPass({ timeout: 15000 })
  131 |         await capture('customer-related-contact-returned')
  132 |       }
  133 |     }
  134 |   } catch (error) {
  135 |     failure = String(error.message)
  136 |     throw error
  137 |   } finally {
  138 |     await save()
  139 |     await context.close()
  140 |   }
  141 | })
  142 |
```
