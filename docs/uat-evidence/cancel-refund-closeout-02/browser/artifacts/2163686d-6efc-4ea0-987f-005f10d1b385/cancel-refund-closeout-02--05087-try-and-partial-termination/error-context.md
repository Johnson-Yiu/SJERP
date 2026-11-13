# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: cancel-refund-closeout-02.spec.js >> A closeout real Chrome cash attribution, cancellation retry and partial termination
- Location: browser-tests\cancel-refund-closeout-02.spec.js:7:1

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: getByRole('dialog', { name: '订单工作台' }).locator('.payment-card')
Expected pattern: /待退款.*900\.00/
Received string:  " 回款状态：部分收款净实收含已分配的预收现金，扣除退款和银行退回。90%应收计划USD 1,000.00净实收USD 900.00当前待收USD 100.00查看 / 登记本单应收"
Timeout: 5000ms

Call log:
  - Expect "toContainText" getByRole('dialog', { name: '订单工作台' }).locator('.payment-card') with timeout 5000ms
  - waiting for getByRole('dialog', { name: '订单工作台' }).locator('.payment-card')
    13 × locator resolved to <article data-v-39de5d98="" class="workbench-card payment-card">…</article>
       - unexpected value " 回款状态：部分收款净实收含已分配的预收现金，扣除退款和银行退回。90%应收计划USD 1,000.00净实收USD 900.00当前待收USD 100.00查看 / 登记本单应收"

```

```yaml
- article:
  - heading "回款状态：部分收款" [level=3]
  - paragraph: 净实收含已分配的预收现金，扣除退款和银行退回。
  - text: 90%
  - term: 应收计划
  - definition: USD 1,000.00
  - term: 净实收
  - definition: USD 900.00
  - term: 当前待收
  - definition: USD 100.00
  - link "查看 / 登记本单应收":
    - /url: /receivables?order=1
```

# Test source

```ts
  1   | import { execFileSync } from 'node:child_process'
  2   | import { chromium, expect, test } from '@playwright/test'
  3   | import { mkdir, readFile, writeFile } from 'node:fs/promises'
  4   | import path from 'node:path'
  5   | import { fileURLToPath } from 'node:url'
  6   | 
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
  47  |         await expect(target).toBeVisible()
  48  |         await target.scrollIntoViewIfNeeded()
  49  |         const metrics = await target.evaluate(el => { const r=el.getBoundingClientRect();return { x:r.x,y:r.y,width:r.width,height:r.height,innerWidth,innerHeight,scrollHeight:el.scrollHeight,clientHeight:el.clientHeight } })
  50  |         expect(metrics.x).toBeGreaterThanOrEqual(-1)
  51  |         expect(metrics.x+metrics.width).toBeLessThanOrEqual(metrics.innerWidth+1)
  52  |         const file = `${name}-${width}-${zoom*100}.png`
  53  |         await page.screenshot({ path:path.join(output,file) })
  54  |         captures.push({ name,width,height,zoom,metrics,file })
  55  |         await save()
  56  |       }
  57  |     }
  58  |     await zoomControl.selectOption('1')
  59  |     await page.setViewportSize({ width:1366,height:768 })
  60  |   }
  61  |   async function refund(f, amount, name) {
  62  |     await page.goto(new URL('/transactions?search=' + f.receiptNo, baseURL).href)
  63  |     await page.getByRole('row').filter({ hasText:f.receiptNo }).getByRole('button',{name:'详情',exact:true}).click()
  64  |     await page.getByRole('button',{name:'从本笔登记退款'}).click()
  65  |     const form=page.getByRole('dialog',{name:'登记退款'})
  66  |     await expect(form.getByLabel('退款对应订单')).toHaveValue(String(f.order))
  67  |     await expect(form.getByLabel('退款对应订单').getByRole('option',{name:'未分配预收款'})).toHaveCount(0)
  68  |     await form.getByLabel(/实际退款金额/).fill(String(amount))
  69  |     await form.getByLabel('退款依据').fill('合成实际原币退款凭证 '+name)
  70  |     await form.getByLabel('实际退款凭证').setInputFiles({name:name+'.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\nSynthetic '+name+'\n%%EOF')})
  71  |     await form.getByRole('button',{name:'上传凭证',exact:true}).click()
  72  |     await expect(form.getByText(/凭证已上传/)).toBeVisible()
  73  |     if(name==='normal-100') await collect('refund-before-submit',form)
  74  |     const saved=page.waitForResponse(r=>r.url().endsWith('/refund-cash/') && r.request().method()==='POST')
  75  |     await form.getByRole('button',{name:'确认登记',exact:true}).click()
  76  |     const response=await saved
  77  |     expect(response.status(),await response.text()).toBe(201)
  78  |     await expect(form).toBeHidden()
  79  |   }
  80  |   try {
  81  |     await refund(fixture.paid,100,'normal-100')
  82  |     await openOrder(fixture.paid)
  83  |     await expect(wb.locator('.payment-card')).toContainText(/100\.00/)
  84  |     await collect('normal-refund-after',wb)
  85  |     await wb.getByRole('button',{name:'取消订单',exact:true}).click()
  86  |     await page.getByLabel('取消原因').fill('合成取消后按原收款分次退款')
  87  |     const cancelForm=page.locator('form').filter({has:page.getByRole('heading',{name:'取消订单',exact:true})})
  88  |     await collect('cancel-before-submit',cancelForm)
  89  |     await page.getByRole('button',{name:'确认取消',exact:true}).click()
> 90  |     await expect(wb.locator('.payment-card')).toContainText(/待退款.*900\.00/)
      |                                               ^ Error: expect(locator).toContainText(expected) failed
  91  |     await collect('cancel-after',wb)
  92  |     await refund(fixture.paid,400,'cancel-400')
  93  |     await openOrder(fixture.paid)
  94  |     await expect(wb.locator('.payment-card')).toContainText(/待退款.*500\.00/)
  95  |     await refund(fixture.paid,500,'cancel-500')
  96  |     await openOrder(fixture.paid)
  97  |     await expect(wb.locator('.payment-card')).not.toContainText('待退款')
  98  |     await collect('cancel-refunds-complete',wb)
  99  |     await openOrder(fixture.partial)
  100 |     await wb.getByRole('button',{name:'取消订单',exact:true}).click()
  101 |     await page.getByLabel('取消原因').fill('部分已发订单应当保留背景与原因')
  102 |     await page.getByRole('button',{name:'确认取消',exact:true}).click()
  103 |     await expect(cancelForm.getByRole('alert')).toBeVisible()
  104 |     await expect(page.getByLabel('取消原因')).toHaveValue('部分已发订单应当保留背景与原因')
  105 |     await collect('cancel-rejection-retained',cancelForm)
  106 |     await cancelForm.getByRole('button',{name:'返回',exact:true}).click()
  107 |     await expect(wb).toBeVisible()
  108 |     await wb.getByRole('button',{name:'调整数量',exact:true}).click()
  109 |     const qty=page.getByRole('dialog',{name:'调整订单数量'})
  110 |     await qty.getByRole('checkbox').check()
  111 |     await qty.getByLabel('新的基础数量 A-CLOSE-SKU',{exact:true}).fill('40')
  112 |     await qty.getByLabel('新的基础数量 A-CLOSE-ZERO',{exact:true}).fill('0')
  113 |     await qty.getByLabel('变更原因').fill('合成部分履约终止，保留已发40件')
  114 |     await qty.getByRole('button',{name:'预览影响'}).click()
  115 |     await expect(qty).toContainText('请先在财务流水')
  116 |     await collect('terminate-paid-refund-guidance',qty)
  117 |     await qty.getByRole('button',{name:'取消',exact:true}).click()
  118 |     await refund(fixture.partial,600,'partial-before-terminate-600')
  119 |     await openOrder(fixture.partial)
  120 |     await wb.getByRole('button',{name:'调整数量',exact:true}).click()
  121 |     await qty.getByRole('checkbox').check()
  122 |     await qty.getByLabel('新的基础数量 A-CLOSE-SKU',{exact:true}).fill('40')
  123 |     await qty.getByLabel('新的基础数量 A-CLOSE-ZERO',{exact:true}).fill('0')
  124 |     await qty.getByLabel('变更原因').fill('实际退回超出履约金额后终止余项')
  125 |     await qty.getByRole('button',{name:'预览影响'}).click()
  126 |     await expect(qty.getByRole('button',{name:'确认调整'})).toBeEnabled()
  127 |     await collect('terminate-before-submit',qty)
  128 |     await qty.getByRole('button',{name:'确认调整'}).click()
  129 |     await page.getByRole('button',{name:'确认提交',exact:true}).last().click()
  130 |     await expect(qty).toBeHidden()
  131 |     await expect(wb).toContainText('已完成')
  132 |     await collect('terminate-after',wb)
  133 |     const details=await (await page.request.get('/api/orders/'+fixture.partial.order+'/workbench/')).json()
  134 |     await writeFile(path.join(output,'final-workbench.json'),JSON.stringify(details,null,2))
  135 |     await save()
  136 |   } finally { await save(); await context.close() }
  137 | })
  138 | 
```