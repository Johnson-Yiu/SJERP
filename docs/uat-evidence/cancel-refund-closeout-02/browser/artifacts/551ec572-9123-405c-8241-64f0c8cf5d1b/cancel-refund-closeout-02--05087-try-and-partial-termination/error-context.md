# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: cancel-refund-closeout-02.spec.js >> A closeout real Chrome cash attribution, cancellation retry and partial termination
- Location: browser-tests\cancel-refund-closeout-02.spec.js:7:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('form').filter({ has: getByRole('heading', { name: '取消订单', exact: true }) }).getByRole('alert')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" locator('form').filter({ has: getByRole('heading', { name: '取消订单', exact: true }) }).getByRole('alert') with timeout 5000ms
  - waiting for locator('form').filter({ has: getByRole('heading', { name: '取消订单', exact: true }) }).getByRole('alert')

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
    - tab "订单管理"
    - button "关闭 订单管理": ×
    - button "订单管理 标签操作": ⋮
    - tab "SO-CLOSE-partial" [selected]
    - button "关闭 SO-CLOSE-partial": ×
    - button "SO-CLOSE-partial 标签操作": ⋮
  - tabpanel "SO-CLOSE-partial":
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
        - strong: "1"
        - text: 仍有应收余额
      - article:
        - text: 已完成
        - strong: "0"
        - text: 已完成交付
    - textbox "搜索订单号或客户": SO-CLOSE-partial
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
        - row "SO-CLOSE-partial 合成取消退款验收客户 2026-11-14 未设置 已确认 2 项 USD 1,200.00 1,000.00 / 200.00":
          - cell "SO-CLOSE-partial"
          - cell "合成取消退款验收客户"
          - cell "2026-11-14"
          - cell "未设置"
          - cell "已确认"
          - cell "2 项"
          - cell "USD 1,200.00"
          - cell "1,000.00 / 200.00"
          - cell
    - dialog "订单工作台":
      - button "关闭订单详情" [disabled]: 关闭
      - text: 订单工作台 · 履约与回款
      - button "开始生产" [disabled]
      - button "取消订单" [disabled]
      - paragraph: 合成取消退款验收客户 · 下单于 2026-11-14
      - heading "SO-CLOSE-partial" [level=2]
      - text: 预计交期：未设置 履约：已确认
      - main:
        - navigation "订单工作台分页":
          - button "概览"
          - button "订单明细 (2)"
          - button "采购与发货"
          - button "回款 (1)"
          - button "装箱"
          - button "库存流水 (0)"
          - button "操作日志 (0)"
        - heading "当前有效双方资料" [level=3]
        - paragraph: 尚未记录；未知资料不会从当前主档补填。
        - heading "买方" [level=4]
        - text: 名称 未知 国家 / 地区 未知 地址 未知 税号 未知 联系人 未知 电话 未知 邮箱 未知 账单地址 未知 收货地址 未知 收件人 未知
        - heading "卖方" [level=4]
        - text: 名称 未知 国家 / 地区 未知 地址 未知 税号 未知 联系人 未知 电话 未知 邮箱 未知 账单地址 未知 收货地址 未知 收件人 未知
        - group: 查看原始双方资料
        - article:
          - heading "原始交易主体快照" [level=3]
          - paragraph: 正式确认时保存的主体资料；后续客户主档修改不会覆盖。更正后的有效版本请查看主体版本。
          - term: 客户名称
          - definition: 合成取消退款验收客户
          - term: 国家/地区
          - definition: 未记录
          - term: 地址
          - definition: 未记录
          - term: 联系人
          - definition: 未记录
          - term: 电话
          - definition: 未记录
          - term: 邮箱
          - definition: 未记录
        - button "查看主体版本与更正"
        - article:
          - heading "订单摘要" [level=3]
          - text: 订单金额
          - strong: USD 1,200.00
          - text: 订单总额 商品项数
          - strong: "2"
          - text: 订单数量
          - strong: "120"
          - text: 预计交期
          - strong: 未设置
        - article:
          - heading "当前待办" [level=3]
          - strong: 待采购
          - paragraph: 还有 2 个 SKU 需要采购。
          - button "查看采购与发货" [disabled]
          - strong: 待发货
          - paragraph: 还有 2 个 SKU 未完成发货。
          - button "查看采购与发货" [disabled]
          - strong: 待收款
          - paragraph: 待收 USD 200.00
          - link "查看 / 登记本单应收":
            - /url: /receivables?order=2
        - article:
          - heading "履约进度" [level=3]
          - paragraph: 按销售出库流水统计。
          - text: 33%
          - term: 订单数量
          - definition: "120"
          - term: 已出库
          - definition: "40"
          - term: 待出库
          - definition: "80"
          - button "查看采购与发货"
        - article:
          - heading "回款状态：部分收款" [level=3]
          - paragraph: 净实收含已分配的预收现金，扣除退款和银行退回。
          - text: 83%
          - term: 应收计划
          - definition: USD 1,200.00
          - term: 净实收
          - definition: USD 1,000.00
          - term: 当前待收
          - definition: USD 200.00
          - link "查看 / 登记本单应收":
            - /url: /receivables?order=2
        - article:
          - heading "成本与毛利" [level=3]
          - term: 分配商品成本
          - definition: ¥ 0.00
          - term: 采购合同调整
          - definition: ¥ 0.00
          - term: 分摊附加费用
          - definition: ¥ 0.00
          - term: 预估总成本
          - definition: ¥ 0.00
          - term: 预估毛利
          - definition: ¥ 1,200.00
        - article:
          - heading "调整订单数量" [level=3]
          - paragraph: 保留订单号和订单行；已发货数量、采购单和收款事实不会被覆盖。
          - button "调整数量"
          - text: 暂无数量变更记录。
        - article:
          - heading "来源报价" [level=3]
          - paragraph: 成交时采用的报价版本。
          - strong: QT-CLOSE-partial-1
          - paragraph: 已接受 · USD 1,200.00
          - button "查看报价工作台"
        - heading "合同金额调整" [level=4]
        - paragraph: 已确认调整会改变当前合同总额；调减只会减少未结清计划，不会自动退款。
        - strong: USD 1,200.00
        - text: 基础金额 USD 1,200.00 已确认调整 USD 0.00
        - spinbutton "调整金额（正/负）"
        - textbox
        - textbox "调整说明"
        - button "新增调整"
        - paragraph: 暂无金额调整记录。
- heading "取消订单" [level=3]
- paragraph: 取消将停止履约，合同金额调为零。已收 USD 1,000.00 将列为待退款，实际退款在财务流水登记。
- text: 取消原因
- textbox "取消原因" [disabled]: 部分已发订单应当保留背景与原因
- contentinfo:
  - button "返回" [disabled]
  - button "提交中…" [disabled]
```

# Test source

```ts
  7   | test('A closeout real Chrome cash attribution, cancellation retry and partial termination', async ({ baseURL }) => {
  8   |   test.setTimeout(1200000)
  9   |   test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== 'cancel-refund-closeout-02.spec.js', 'isolated fixture only')
  10  |   const repo = fileURLToPath(new URL('../../', import.meta.url))
  11  |   const output = path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome')
  12  |   await mkdir(output, { recursive: true })
  13  |   const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON,
  14  |     [path.join(repo, 'docs/uat-evidence/cancel-refund-closeout-02/seed.py')],
  15  |     { cwd: path.join(repo, 'backend'), encoding: 'utf8', env: { ...process.env, PYTHONUTF8: '1' } }))
  16  |   const context = await chromium.launchPersistentContext(path.join(process.env.ISOLATED_TEST_ROOT, 'a-close-chrome'), { channel: 'chrome', viewport: { width: 1366, height: 768 } })
  17  |   context.setDefaultTimeout(30000)
  18  |   const auth = JSON.parse(await readFile(path.join(process.env.ISOLATED_TEST_ROOT, 'codex-auth.json'), 'utf8'))
  19  |   await context.addCookies(auth.cookies)
  20  |   const settings = context.pages()[0]
  21  |   await settings.goto('chrome://settings/appearance', { waitUntil: 'commit' })
  22  |   const zoomControl = settings.locator('settings-appearance-page select').filter({ has: settings.locator('option[value="1.25"]') })
  23  |   await expect(zoomControl).toBeVisible({ timeout: 90000 })
  24  |   const page = await context.newPage()
  25  |   const cdp = await context.newCDPSession(page)
  26  |   const browser = (await cdp.send('Browser.getVersion')).product
  27  |   expect(browser).toMatch(/^Chrome\//)
  28  |   const events = [], captures = []
  29  |   page.on('response', async r => {
  30  |     if (r.request().method() === 'POST' && /refund-cash|\/cancel\/|quantity-adjustments/.test(r.url())) {
  31  |       events.push({ url: new URL(r.url()).pathname, status: r.status(), request: r.request().postDataJSON(), response: await r.json().catch(() => null) })
  32  |     }
  33  |   })
  34  |   const save = async () => writeFile(path.join(output, 'run.json'), JSON.stringify({ browser, fixture, events, captures }, null, 2))
  35  |   const wb = page.getByRole('dialog', { name: '订单工作台' })
  36  |   async function openOrder(f) {
  37  |     await page.goto(new URL('/orders?search=' + f.number, baseURL).href)
  38  |     await page.getByRole('row').filter({ hasText: f.number }).click()
  39  |     await expect(wb).toBeVisible()
  40  |   }
  41  |   async function collect(name, target) {
  42  |     for (const zoom of [1, 1.25]) {
  43  |       await zoomControl.selectOption(String(zoom))
  44  |       for (const [width,height] of [[1366,768],[1920,1080],[390,844]]) {
  45  |         await page.setViewportSize({ width,height })
  46  |         await expect.poll(() => page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
  47  |         if (width===390) await expect.poll(() => page.locator('.sidebar').evaluate(el=>el.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
  48  |         await expect(target).toBeVisible()
  49  |         await target.scrollIntoViewIfNeeded()
  50  |         const metrics = await target.evaluate(el => { const r=el.getBoundingClientRect();return { x:r.x,y:r.y,width:r.width,height:r.height,innerWidth,innerHeight,scrollHeight:el.scrollHeight,clientHeight:el.clientHeight } })
  51  |         expect(metrics.x).toBeGreaterThanOrEqual(-1)
  52  |         expect(metrics.x+metrics.width).toBeLessThanOrEqual(metrics.innerWidth+1)
  53  |         const file = `${name}-${width}-${zoom*100}.png`
  54  |         await page.screenshot({ path:path.join(output,file) })
  55  |         captures.push({ name,width,height,zoom,metrics,file })
  56  |         await save()
  57  |       }
  58  |     }
  59  |     await zoomControl.selectOption('1')
  60  |     await page.setViewportSize({ width:1366,height:768 })
  61  |   }
  62  |   async function refund(f, amount, name) {
  63  |     await page.goto(new URL('/transactions?search=' + f.receiptNo, baseURL).href)
  64  |     await page.getByRole('row').filter({ hasText:f.receiptNo }).getByRole('button',{name:'详情',exact:true}).click()
  65  |     await page.getByRole('button',{name:'从本笔登记退款'}).click()
  66  |     const form=page.getByRole('dialog',{name:'登记退款'})
  67  |     await expect(form.getByLabel('退款对应订单')).toHaveValue(String(f.order))
  68  |     await expect(form.getByLabel('退款对应订单').getByRole('option',{name:'未分配预收款'})).toHaveCount(0)
  69  |     await form.getByLabel(/实际退款金额/).fill(String(amount))
  70  |     await form.getByLabel('退款依据').fill('合成实际原币退款凭证 '+name)
  71  |     await form.getByLabel('实际退款凭证').setInputFiles({name:name+'.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\nSynthetic '+name+'\n%%EOF')})
  72  |     await form.getByRole('button',{name:'上传凭证',exact:true}).click()
  73  |     await expect(form.getByText(/凭证已上传/)).toBeVisible()
  74  |     if(name==='normal-100') await collect('refund-before-submit',form)
  75  |     const saved=page.waitForResponse(r=>r.url().endsWith('/refund-cash/') && r.request().method()==='POST')
  76  |     await form.getByRole('button',{name:'确认登记',exact:true}).click()
  77  |     const response=await saved
  78  |     expect(response.status(),await response.text()).toBe(201)
  79  |     await expect(form).toBeHidden()
  80  |   }
  81  |   try {
  82  |     await refund(fixture.paid,100,'normal-100')
  83  |     await openOrder(fixture.paid)
  84  |     await expect(wb.locator('.payment-card')).toContainText(/100\.00/)
  85  |     await collect('normal-refund-after',wb)
  86  |     await wb.getByRole('button',{name:'取消订单',exact:true}).click()
  87  |     await page.getByLabel('取消原因').fill('合成取消后按原收款分次退款')
  88  |     const cancelForm=page.locator('form').filter({has:page.getByRole('heading',{name:'取消订单',exact:true})})
  89  |     await collect('cancel-before-submit',cancelForm)
  90  |     const cancelled=page.waitForResponse(r=>r.url().endsWith('/cancel/') && r.request().method()==='POST')
  91  |     await page.getByRole('button',{name:'确认取消',exact:true}).click()
  92  |     const cancellation=await cancelled
  93  |     expect(cancellation.status(),await cancellation.text()).toBe(200)
  94  |     await expect(wb.locator('.payment-card')).toContainText(/待退款.*900\.00/, {timeout:20000})
  95  |     await collect('cancel-after',wb)
  96  |     await refund(fixture.paid,400,'cancel-400')
  97  |     await openOrder(fixture.paid)
  98  |     await expect(wb.locator('.payment-card')).toContainText(/待退款.*500\.00/)
  99  |     await refund(fixture.paid,500,'cancel-500')
  100 |     await openOrder(fixture.paid)
  101 |     await expect(wb.locator('.payment-card')).not.toContainText('待退款')
  102 |     await collect('cancel-refunds-complete',wb)
  103 |     await openOrder(fixture.partial)
  104 |     await wb.getByRole('button',{name:'取消订单',exact:true}).click()
  105 |     await page.getByLabel('取消原因').fill('部分已发订单应当保留背景与原因')
  106 |     await page.getByRole('button',{name:'确认取消',exact:true}).click()
> 107 |     await expect(cancelForm.getByRole('alert')).toBeVisible()
      |                                                 ^ Error: expect(locator).toBeVisible() failed
  108 |     await expect(page.getByLabel('取消原因')).toHaveValue('部分已发订单应当保留背景与原因')
  109 |     await collect('cancel-rejection-retained',cancelForm)
  110 |     await cancelForm.getByRole('button',{name:'返回',exact:true}).click()
  111 |     await expect(wb).toBeVisible()
  112 |     await wb.getByRole('button',{name:'调整数量',exact:true}).click()
  113 |     const qty=page.getByRole('dialog',{name:'调整订单数量'})
  114 |     await qty.getByRole('checkbox').check()
  115 |     await qty.getByLabel('新的基础数量 A-CLOSE-SKU',{exact:true}).fill('40')
  116 |     await qty.getByLabel('新的基础数量 A-CLOSE-ZERO',{exact:true}).fill('0')
  117 |     await qty.getByLabel('变更原因').fill('合成部分履约终止，保留已发40件')
  118 |     await qty.getByRole('button',{name:'预览影响'}).click()
  119 |     await expect(qty).toContainText('请先在财务流水')
  120 |     await collect('terminate-paid-refund-guidance',qty)
  121 |     await qty.getByRole('button',{name:'取消',exact:true}).click()
  122 |     await refund(fixture.partial,600,'partial-before-terminate-600')
  123 |     await openOrder(fixture.partial)
  124 |     await wb.getByRole('button',{name:'调整数量',exact:true}).click()
  125 |     await qty.getByRole('checkbox').check()
  126 |     await qty.getByLabel('新的基础数量 A-CLOSE-SKU',{exact:true}).fill('40')
  127 |     await qty.getByLabel('新的基础数量 A-CLOSE-ZERO',{exact:true}).fill('0')
  128 |     await qty.getByLabel('变更原因').fill('实际退回超出履约金额后终止余项')
  129 |     await qty.getByRole('button',{name:'预览影响'}).click()
  130 |     await expect(qty.getByRole('button',{name:'确认调整'})).toBeEnabled()
  131 |     await collect('terminate-before-submit',qty)
  132 |     await qty.getByRole('button',{name:'确认调整'}).click()
  133 |     await page.getByRole('button',{name:'确认提交',exact:true}).last().click()
  134 |     await expect(qty).toBeHidden()
  135 |     await expect(wb).toContainText('已完成')
  136 |     await collect('terminate-after',wb)
  137 |     const details=await (await page.request.get('/api/orders/'+fixture.partial.order+'/workbench/')).json()
  138 |     await writeFile(path.join(output,'final-workbench.json'),JSON.stringify(details,null,2))
  139 |     await save()
  140 |   } finally { await save(); await context.close() }
  141 | })
  142 | 
```