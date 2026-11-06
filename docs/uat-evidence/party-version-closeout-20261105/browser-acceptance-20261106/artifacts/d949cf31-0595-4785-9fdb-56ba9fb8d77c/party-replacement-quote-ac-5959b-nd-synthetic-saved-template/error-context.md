# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: party-replacement-quote-acceptance-20261106.spec.js >> synthetic quote replacement uses independent approval and synthetic saved template
- Location: browser-tests\party-replacement-quote-acceptance-20261106.spec.js:7:1

# Error details

```
Error: Traceback (most recent call last):
  File "D:\Codex项目\森爵照明管理系统\.worktrees\party-version-closeout-20261105\docs\uat-evidence\party-version-closeout-20261105\browser-acceptance-20261106\seed_quote_extended.py", line 30, in <module>
    copy2(source_root / config.file, target)
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python314\Lib\shutil.py", line 514, in copy2
    _winapi.CopyFile2(src_, dst_, flags)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
PermissionError: [WinError 32] 另一个程序正在使用此文件，进程无法访问。


expect(received).toBe(expected) // Object.is equality

Expected: 0
Received: 1
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import { spawnSync } from 'node:child_process'
  3  | import fs from 'node:fs'
  4  | import path from 'node:path'
  5  | 
  6  | test.use({ channel: 'chrome', viewport: { width: 390, height: 844 } })
  7  | test('synthetic quote replacement uses independent approval and synthetic saved template', async ({ browser, baseURL }) => {
  8  |   test.setTimeout(180000)
  9  |   const root = path.resolve('../docs/uat-evidence/party-version-closeout-20261105/browser-acceptance-20261106')
  10 |   const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(root, 'seed_quote_extended.py')], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
> 11 |   expect(seed.status, seed.stderr).toBe(0)
     |                                    ^ Error: Traceback (most recent call last):
  12 |   const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  13 |   const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'replacement-quote')
  14 |   fs.mkdirSync(evidence, { recursive: true })
  15 |   const apiBase = process.env.ISOLATED_PLAYWRIGHT_API_BASE_URL
  16 |   const a = await browser.newContext({ viewport: { width: 1440, height: 900 } }), b = await browser.newContext({ viewport: { width: 390, height: 844 } })
  17 |   async function login(context, username) {
  18 |     const p = await context.newPage(); await p.goto(`${apiBase}/admin/login/`)
  19 |     await p.locator('[name="username"]').fill(username); await p.locator('[name="password"]').fill('synthetic-only-password')
  20 |     await p.locator('input[type="submit"]').click(); await expect(p).not.toHaveURL(/\/admin\/login/); await p.close()
  21 |   }
  22 |   async function open(context) {
  23 |     const p = await context.newPage(); await p.goto(new URL(`/quotes?detail=${fixture.quote}`, baseURL).toString())
  24 |     await p.getByRole('button', { name: '主体更正' }).click()
  25 |     await expect(p.locator('.party-change-panel')).toContainText('主体变更申请')
  26 |     return p
  27 |   }
  28 |   try {
  29 |     await login(a, fixture.first_username); await login(b, fixture.second_username)
  30 |     const maker = await open(a), panel = maker.locator('.party-change-panel')
  31 |     await panel.locator('.party-change-type select').selectOption('replacement')
  32 |     const form = panel.locator('.replacement-form')
  33 |     await form.getByLabel('目标客户').selectOption(String(fixture.target))
  34 |     while (await form.getByRole('button', { name: '确认留空' }).count()) await form.getByRole('button', { name: '确认留空' }).first().click()
  35 |     await form.getByLabel('原因').fill('Synthetic replacement'); await form.getByLabel('依据').fill('Synthetic evidence')
  36 |     const proposed = maker.waitForResponse(r => r.url().endsWith('/party-change/') && r.request().method() === 'POST')
  37 |     await form.getByRole('button', { name: '提交替换申请' }).click(); expect((await proposed).status()).toBe(201)
  38 |     const reviewer = await open(b), review = reviewer.locator('.party-change-panel')
  39 |     await review.locator('.party-request').first().scrollIntoViewIfNeeded(); await reviewer.screenshot({ path: path.join(evidence, 'review-390.png') })
  40 |     await maker.reload(); await maker.getByRole('button', { name: '主体更正' }).click(); await maker.locator('.party-request').first().scrollIntoViewIfNeeded(); await maker.screenshot({ path: path.join(evidence, 'review-desktop.png') })
  41 |     await review.locator('.party-request .party-approval-note input').first().fill('Synthetic independent review')
  42 |     const approved = reviewer.waitForResponse(r => r.url().includes('/approve/') && r.request().method() === 'POST')
  43 |     await review.getByRole('button', { name: '批准主体替换记录' }).click(); expect((await approved).status()).toBe(200)
  44 |     await review.getByRole('button', { name: '填写关联新单' }).click()
  45 |     const draft = review.locator('.replacement-form')
  46 |     await draft.getByLabel('单据日期').fill('2026-11-05'); await draft.getByLabel('币种').fill('USD'); await draft.getByLabel('汇率').fill('7.2')
  47 |     await draft.getByLabel('运费').fill('0'); await draft.getByLabel('折扣').fill('0'); await draft.getByLabel('定金比例').fill('0.3')
  48 |     await draft.getByLabel('SKU').selectOption(String(fixture.sku)); await draft.getByLabel('数量').fill('3'); await draft.getByLabel('单价').fill('5')
  49 |     await draft.getByLabel('已核对全部新单资料和条款').check()
  50 |     await draft.scrollIntoViewIfNeeded(); await reviewer.screenshot({ path: path.join(evidence, 'new-draft-390.png') })
  51 |     const created = reviewer.waitForResponse(r => r.url().includes('/create-replacement/') && r.request().method() === 'POST')
  52 |     await draft.getByRole('button', { name: '创建关联草稿' }).click()
  53 |     const response = await created
  54 |     if (!response.ok()) console.error('Replacement creation response:', response.status(), await response.text())
  55 |     expect(response.status()).toBe(200)
  56 |     const result = await response.json(); expect(result.result_quote_id).toBeTruthy()
  57 |     const saved = await (await reviewer.request.get(`${apiBase}/api/quotes/${result.result_quote_id}/`)).json()
  58 |     expect(saved.status).toBe('draft'); expect(saved.customer).toBe(fixture.target)
  59 |     expect(saved.buyer_country_snapshot).toBe('')
  60 |     const pi = await reviewer.request.get(`${apiBase}/api/quotes/${result.result_quote_id}/pi-data/`)
  61 |     expect(pi.status()).toBe(200); expect((await pi.json()).seller.name).toBe('Synthetic Seller')
  62 |     fs.writeFileSync(path.join(evidence, 'http-results.json'), JSON.stringify({ proposal: 201, approval: 200, created: response.status(), pi: pi.status(), result_quote_id: result.result_quote_id }, null, 2))
  63 |   } finally { await a.close(); await b.close() }
  64 | })
  65 | 
```