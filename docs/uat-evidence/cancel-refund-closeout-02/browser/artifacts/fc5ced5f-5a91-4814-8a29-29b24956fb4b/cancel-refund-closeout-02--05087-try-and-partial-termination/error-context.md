# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: cancel-refund-closeout-02.spec.js >> A closeout real Chrome cash attribution, cancellation retry and partial termination
- Location: browser-tests\cancel-refund-closeout-02.spec.js:9:1

# Error details

```
Error: Command failed: python D:\Codex项目\森爵照明管理系统\.worktrees\cancel-refund-closeout-02\docs\uat-evidence\cancel-refund-closeout-02\seed.py
Traceback (most recent call last):
  File "D:\Codex项目\森爵照明管理系统\.worktrees\cancel-refund-closeout-02\docs\uat-evidence\cancel-refund-closeout-02\seed.py", line 26, in <module>
    writeoff_receivable(receipt, order.payment_plans.get(), __import__("decimal").Decimal("1"), "合成授权抹零夹具", "a2-reduction", None)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\contextlib.py", line 85, in inner
    return func(*args, **kwds)
  File "D:\Codex项目\森爵照明管理系统\.worktrees\cancel-refund-closeout-02\backend\crm\services\finance.py", line 51, in writeoff_receivable
    require_finance_permission(user, "finance", "update")
    ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Codex项目\森爵照明管理系统\.worktrees\cancel-refund-closeout-02\backend\crm\finance_scope.py", line 13, in require_finance_permission
    raise PermissionDenied("你没有权限执行此财务操作。")
rest_framework.exceptions.PermissionDenied: 你没有权限执行此财务操作。

```

# Test source

```ts
  1   | import { execFileSync } from 'node:child_process'
  2   | import { chromium, expect as baseExpect, test } from '@playwright/test'
  3   | import { mkdir, readFile, writeFile } from 'node:fs/promises'
  4   | import path from 'node:path'
  5   | import { fileURLToPath } from 'node:url'
  6   | 
  7   | const expect = baseExpect.configure({ timeout: 30000 })
  8   | 
  9   | test('A closeout real Chrome cash attribution, cancellation retry and partial termination', async ({ baseURL }) => {
  10  |   test.setTimeout(1200000)
  11  |   test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== 'cancel-refund-closeout-02.spec.js', 'isolated fixture only')
  12  |   const repo = fileURLToPath(new URL('../../', import.meta.url))
  13  |   const output = path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome')
  14  |   await mkdir(output, { recursive: true })
> 15  |   const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON,
      |                              ^ Error: Command failed: python D:\Codex项目\森爵照明管理系统\.worktrees\cancel-refund-closeout-02\docs\uat-evidence\cancel-refund-closeout-02\seed.py
  16  |     [path.join(repo, 'docs/uat-evidence/cancel-refund-closeout-02/seed.py')],
  17  |     { cwd: path.join(repo, 'backend'), encoding: 'utf8', env: { ...process.env, PYTHONUTF8: '1' } }))
  18  |   const context = await chromium.launchPersistentContext(path.join(process.env.ISOLATED_TEST_ROOT, 'a-close-chrome'), { channel: 'chrome', viewport: { width: 1366, height: 768 } })
  19  |   context.setDefaultTimeout(30000)
  20  |   const auth = JSON.parse(await readFile(path.join(process.env.ISOLATED_TEST_ROOT, 'codex-auth.json'), 'utf8'))
  21  |   await context.addCookies(auth.cookies)
  22  |   const settings = context.pages()[0]
  23  |   await settings.goto('chrome://settings/appearance', { waitUntil: 'commit' })
  24  |   const zoomControl = settings.locator('settings-appearance-page select').filter({ has: settings.locator('option[value="1.25"]') })
  25  |   await expect(zoomControl).toBeVisible({ timeout: 90000 })
  26  |   const page = await context.newPage()
  27  |   const cdp = await context.newCDPSession(page)
  28  |   const browser = (await cdp.send('Browser.getVersion')).product
  29  |   expect(browser).toMatch(/^Chrome\//)
  30  |   const events = [], captures = []
  31  |   page.on('response', async r => {
  32  |     if (r.request().method() === 'POST' && /refund-cash|\/cancel\/|quantity-adjustments|\/void\/|writeoff/.test(r.url())) {
  33  |       events.push({ url: new URL(r.url()).pathname, status: r.status(), request: r.request().postDataJSON(), response: await r.json().catch(() => null) })
  34  |     }
  35  |   })
  36  |   const save = async () => writeFile(path.join(output, 'run.json'), JSON.stringify({ browser, fixture, events, captures }, null, 2))
  37  |   const wb = page.getByRole('dialog', { name: '订单工作台' })
  38  |   async function openOrder(f) {
  39  |     await page.goto(new URL('/orders?search=' + f.number, baseURL).href)
  40  |     await page.getByRole('row').filter({ hasText: f.number }).click()
  41  |     await expect(wb).toBeVisible()
  42  |   }
  43  |   async function collect(name, target) {
  44  |     for (const zoom of [1, 1.25]) {
  45  |       await zoomControl.selectOption(String(zoom))
  46  |       for (const [width,height] of [[1366,768],[1920,1080],[390,844]]) {
  47  |         await page.setViewportSize({ width,height })
  48  |         await expect.poll(() => page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
  49  |         if (width===390) await expect.poll(() => page.locator('.sidebar').evaluate(el=>el.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
  50  |         await expect(target).toBeVisible()
  51  |         await target.scrollIntoViewIfNeeded()
  52  |         const metrics = await target.evaluate(el => { const r=el.getBoundingClientRect();return { x:r.x,y:r.y,width:r.width,height:r.height,innerWidth,innerHeight,scrollHeight:el.scrollHeight,clientHeight:el.clientHeight } })
  53  |         expect(metrics.x).toBeGreaterThanOrEqual(-1)
  54  |         expect(metrics.x+metrics.width).toBeLessThanOrEqual(metrics.innerWidth+1)
  55  |         const file = `${name}-${width}-${zoom*100}.png`
  56  |         await page.screenshot({ path:path.join(output,file) })
  57  |         captures.push({ name,width,height,zoom,metrics,file })
  58  |         await save()
  59  |       }
  60  |     }
  61  |     await zoomControl.selectOption('1')
  62  |     await page.setViewportSize({ width:1366,height:768 })
  63  |   }
  64  |   async function refund(f, amount, name) {
  65  |     await page.goto(new URL('/transactions?search=' + f.receiptNo, baseURL).href)
  66  |     await page.getByRole('row').filter({ hasText:f.receiptNo }).getByRole('button',{name:'详情',exact:true}).click()
  67  |     await page.getByRole('button',{name:'从本笔登记退款'}).click()
  68  |     const form=page.getByRole('dialog',{name:'登记退款'})
  69  |     await expect(form.getByLabel('退款对应订单')).toHaveValue(String(f.order))
  70  |     await expect(form.getByLabel('退款对应订单').getByRole('option',{name:'未分配预收款'})).toHaveCount(0)
  71  |     await form.getByLabel(/实际退款金额/).fill(String(amount))
  72  |     await form.getByLabel('退款依据').fill('合成实际原币退款凭证 '+name)
  73  |     await form.getByLabel('实际退款凭证').setInputFiles({name:name+'.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\nSynthetic '+name+'\n%%EOF')})
  74  |     await form.getByRole('button',{name:'上传凭证',exact:true}).click()
  75  |     await expect(form.getByText(/凭证已上传/)).toBeVisible()
  76  |     if(name==='normal-100') await collect('refund-before-submit',form)
  77  |     const saved=page.waitForResponse(r=>r.url().endsWith('/refund-cash/') && r.request().method()==='POST')
  78  |     await form.getByRole('button',{name:'确认登记',exact:true}).click()
  79  |     const response=await saved
  80  |     expect(response.status(),await response.text()).toBe(201)
  81  |     await expect(form).toBeHidden()
  82  |   }
  83  |   try {
  84  |     await refund(fixture.paid,100,'normal-100')
  85  |     await openOrder(fixture.paid)
  86  |     await expect(wb.locator('.payment-card')).toContainText(/100\.00/)
  87  |     await collect('normal-refund-after',wb)
  88  |     await wb.getByRole('button',{name:'取消订单',exact:true}).click()
  89  |     await page.getByLabel('取消原因').fill('合成取消后按原收款分次退款')
  90  |     const cancelForm=page.locator('form').filter({has:page.getByRole('heading',{name:'取消订单',exact:true})})
  91  |     await collect('cancel-before-submit',cancelForm)
  92  |     const cancelled=page.waitForResponse(r=>r.url().endsWith('/cancel/') && r.request().method()==='POST')
  93  |     await page.getByRole('button',{name:'确认取消',exact:true}).click()
  94  |     const cancellation=await cancelled
  95  |     expect(cancellation.status(),await cancellation.text()).toBe(200)
  96  |     await expect(wb.locator('.payment-card')).toContainText(/待退款.*900\.00/, {timeout:20000})
  97  |     await collect('cancel-after',wb)
  98  |     await refund(fixture.paid,400,'cancel-400')
  99  |     await openOrder(fixture.paid)
  100 |     await expect(wb.locator('.payment-card')).toContainText(/待退款.*500\.00/)
  101 |     await refund(fixture.paid,500,'cancel-500')
  102 |     await openOrder(fixture.paid)
  103 |     await expect(wb.locator('.payment-card')).not.toContainText('待退款')
  104 |     await collect('cancel-refunds-complete',wb)
  105 |     await openOrder(fixture.partial)
  106 |     await wb.getByRole('button',{name:'取消订单',exact:true}).click()
  107 |     await page.getByLabel('取消原因').fill('部分已发订单应当保留背景与原因')
  108 |     const refused=page.waitForResponse(r=>r.url().endsWith('/cancel/') && r.request().method()==='POST')
  109 |     await page.getByRole('button',{name:'确认取消',exact:true}).click()
  110 |     expect((await refused).status()).toBe(400)
  111 |     await expect(cancelForm.getByRole('alert')).toBeVisible()
  112 |     await expect(page.getByLabel('取消原因')).toHaveValue('部分已发订单应当保留背景与原因')
  113 |     await collect('cancel-rejection-retained',cancelForm)
  114 |     await cancelForm.getByRole('button',{name:'返回',exact:true}).click()
  115 |     await expect(wb).toBeVisible()
```