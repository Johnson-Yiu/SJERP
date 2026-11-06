# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: party-document-real.spec.js >> formal SO and PO corrections retain original snapshots and business facts
- Location: browser-tests\party-document-real.spec.js:8:1

# Error details

```
Error: locator.scrollIntoViewIfNeeded: Element is not attached to the DOM
Call log:
  - attempting scroll into view action
    - waiting for element to be stable

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import { spawnSync } from 'node:child_process'
  3  | import fs from 'node:fs'
  4  | import path from 'node:path'
  5  | 
  6  | test.use({ channel: 'chrome' })
  7  | 
  8  | test('formal SO and PO corrections retain original snapshots and business facts', async ({ browser, page, baseURL }) => {
  9  |   test.setTimeout(120000)
  10 |   expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  11 |   const root = path.resolve('../docs/uat-evidence/party-version-closeout-02')
  12 |   const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(root, 'seed_document_party.py')], {
  13 |     cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  14 |   })
  15 |   expect(seed.status, seed.stderr).toBe(0)
  16 |   const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  17 |   const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'document-party')
  18 |   fs.mkdirSync(evidence, { recursive: true })
  19 |   const apiBase = process.env.ISOLATED_PLAYWRIGHT_API_BASE_URL
  20 |   async function login(context, username) {
  21 |     const auth = await context.newPage()
  22 |     await auth.goto(`${apiBase}/admin/login/`)
  23 |     await auth.locator('[name="username"]').fill(username)
  24 |     await auth.locator('[name="password"]').fill('synthetic-only-password')
  25 |     await auth.locator('input[type="submit"]').click()
  26 |     await expect(auth).not.toHaveURL(/\/admin\/login/)
  27 |     await auth.close()
  28 |   }
  29 |   const a = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  30 |   const b = await browser.newContext({ viewport: { width: 390, height: 844 } })
  31 |   try {
  32 |     await login(a, fixture.first_username); await login(b, fixture.second_username)
  33 |     const first = await a.newPage(), second = await b.newPage(), results = []
  34 |     for (const [kind, route, id, snapshotField] of [['order', 'orders', fixture.order, 'customer_address_snapshot'], ['purchase', 'purchase-orders', fixture.purchase, 'supplier_address_snapshot']]) {
  35 |       const before = await (await page.request.get(`/api/${route}/${id}/`)).json()
  36 |       const url = new URL(`/${route}?detail=${id}`, baseURL).toString()
  37 |       async function open(p) {
  38 |         await p.goto(url)
  39 |         await p.getByRole('button', { name: '查看主体版本与更正' }).click()
  40 |         await expect(p.locator('.document-party-versions')).toContainText('当前有效主体资料')
  41 |       }
  42 |       await open(first)
  43 |       const panel = first.locator('.document-party-versions')
  44 |       await panel.getByLabel('地址', { exact: true }).fill(`Synthetic corrected ${kind} address`)
  45 |       await panel.getByLabel('原因', { exact: true }).fill('Synthetic reason')
  46 |       await panel.getByLabel('依据', { exact: true }).fill('Synthetic evidence')
  47 |       await panel.getByLabel('已核对依据，确认法律主体未变').check()
  48 |       const proposal = first.waitForResponse(r => r.url().endsWith('/party-change/') && r.request().method() === 'POST')
  49 |       await panel.getByRole('button', { name: '提交更正申请' }).click()
  50 |       expect((await proposal).status()).toBe(201)
  51 |       await open(second)
  52 |       const review = second.locator('.document-party-versions')
  53 |       await review.getByLabel('审批意见 / 处理原因').fill('Independent synthetic review')
  54 |       const approval = second.waitForResponse(r => r.url().includes('/approve/') && r.request().method() === 'POST')
  55 |       await review.getByRole('button', { name: '批准更正' }).click()
  56 |       expect((await approval).status()).toBe(200)
  57 |       await expect(review.getByText('已批准', { exact: false }).first()).toBeVisible()
  58 |       const applied = second.waitForResponse(r => r.url().includes('/apply/') && r.request().method() === 'POST')
  59 |       await review.getByRole('button', { name: '生效主体更正' }).click()
  60 |       expect((await applied).status()).toBe(200)
  61 |       await expect(review).toContainText(`Synthetic corrected ${kind} address`)
> 62 |       await review.getByText(`Synthetic corrected ${kind} address`).first().scrollIntoViewIfNeeded()
     |                                                                             ^ Error: locator.scrollIntoViewIfNeeded: Element is not attached to the DOM
  63 |       await second.screenshot({ path: path.join(evidence, `${kind}-390.png`) })
  64 |       await first.reload(); await first.getByRole('button', { name: '查看主体版本与更正' }).click()
  65 |       await expect(first.locator('.document-party-versions')).toContainText(`Synthetic corrected ${kind} address`)
  66 |       await first.locator('.document-party-versions').scrollIntoViewIfNeeded()
  67 |       await first.screenshot({ path: path.join(evidence, `${kind}-desktop.png`) })
  68 |       const afterResponse = await page.request.get(`/api/${route}/${id}/`)
  69 |       const after = await afterResponse.json()
  70 |       expect(after[snapshotField]).toBe(before[snapshotField])
  71 |       expect(after.total_amount).toBe(before.total_amount)
  72 |       expect(after.items).toEqual(before.items)
  73 |       results.push({ kind, id, get: afterResponse.status(), proposal: 201, approval: 200, apply: 200, originalAddress: after[snapshotField], total: after.total_amount })
  74 |     }
  75 |     fs.writeFileSync(path.join(evidence, 'http-results.json'), JSON.stringify(results, null, 2))
  76 |   } finally { await a.close(); await b.close() }
  77 | })
  78 | 
```