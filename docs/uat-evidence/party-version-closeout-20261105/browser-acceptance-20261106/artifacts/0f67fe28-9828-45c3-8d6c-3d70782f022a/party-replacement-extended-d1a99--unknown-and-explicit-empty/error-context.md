# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: party-replacement-extended-20261106.spec.js >> extended replacement: two accounts, facts, unknown and explicit empty
- Location: browser-tests\party-replacement-extended-20261106.spec.js:7:1

# Error details

```
Error: Traceback (most recent call last):
  File "D:\Codex项目\森爵照明管理系统\.worktrees\party-version-closeout-20261105\docs\uat-evidence\party-version-closeout-20261105\browser-acceptance-20261106\seed_extended.py", line 9, in <module>
    runpy.run_path(str(root / 'seed_replacement_browser.py'), run_name='__main__')
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen runpy>", line 293, in run_path
  File "<frozen runpy>", line 261, in _get_code_from_file
FileNotFoundError: [Errno 2] No such file or directory: 'D:\\Codex项目\\森爵照明管理系统\\.worktrees\\party-version-closeout-20261105\\docs\\uat-evidence\\party-version-closeout-20261105\\party-version-closeout-02\\seed_replacement_browser.py'


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
  6  | test.use({ channel: 'chrome' })
  7  | test('extended replacement: two accounts, facts, unknown and explicit empty', async ({ browser, baseURL }) => {
  8  |   test.setTimeout(240000)
  9  |   const root = path.resolve('../docs/uat-evidence/party-version-closeout-20261105/browser-acceptance-20261106')
  10 |   const evidence = path.join(root, 'extended')
  11 |   fs.mkdirSync(evidence, { recursive: true })
  12 |   const run = (name, args = []) => {
  13 |     const x = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(root, name), ...args], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
> 14 |     expect(x.status, x.stderr).toBe(0)
     |                                ^ Error: Traceback (most recent call last):
  15 |     return JSON.parse(x.stdout.trim().split('\n').at(-1))
  16 |   }
  17 |   const f = run('seed_extended.py'), api = process.env.ISOLATED_PLAYWRIGHT_API_BASE_URL
  18 |   const snapshot = () => run('snapshot_extended.py', [String(f.order), String(f.purchase)])
  19 |   const before = snapshot()
  20 |   fs.writeFileSync(path.join(evidence, 'source-before.json'), JSON.stringify(before, null, 2))
  21 |   expect(before.transactions).toHaveLength(2); expect(before.receipts).toHaveLength(1); expect(before.shipments).toHaveLength(1)
  22 |   const a = await browser.newContext({ viewport: { width: 1440, height: 900 } }), b = await browser.newContext({ viewport: { width: 390, height: 844 } })
  23 |   const logs = []
  24 |   async function login(c, user) {
  25 |     const p = await c.newPage(); await p.goto(`${api}/admin/login/`); await p.locator('[name=username]').fill(user); await p.locator('[name=password]').fill('synthetic-only-password'); await p.locator('input[type=submit]').click(); await expect(p).not.toHaveURL(/admin\/login/); await p.close()
  26 |   }
  27 |   try {
  28 |     await login(a, f.first_username); await login(b, f.second_username)
  29 |     for (const kind of ['order', 'purchase']) {
  30 |       const isOrder = kind === 'order', route = isOrder ? 'orders' : 'purchase-orders', id = f[kind], side = isOrder ? 'buyer' : 'seller', target = isOrder ? f.replacement_customer : f.replacement_supplier
  31 |       const maker = await a.newPage(), reviewer = await b.newPage(), url = new URL(`/${route}?detail=${id}`, baseURL).toString()
  32 |       async function open(page) { await page.goto(url); await page.getByRole('button', { name: '查看主体版本与更正' }).click(); await expect(page.locator('.document-party-versions')).toContainText('当前有效主体资料') }
  33 |       await open(maker); let panel = maker.locator('.document-party-versions')
  34 |       await panel.getByRole('button', { name: '申请更换法律主体' }).click()
  35 |       let form = panel.locator('.replacement-form')
  36 |       await form.getByLabel(isOrder ? '目标客户' : '目标供应商').selectOption(String(target))
  37 |       const basic = form.locator(':scope > label').filter({ hasText: /^拟议/ })
  38 |       for (let i = 0; i < await basic.count(); i++) { const btn = basic.nth(i).getByRole('button', { name: '确认留空' }); if (await btn.count()) await btn.click() }
  39 |       const extended = form.locator('fieldset').filter({ has: maker.getByText(isOrder ? '买方扩展资料' : '卖方扩展资料', { exact: true }) })
  40 |       await extended.getByLabel('账单地址').fill(`Synthetic new ${kind} billing`)
  41 |       await extended.locator('label').filter({ hasText: /^税号/ }).getByRole('button', { name: '确认留空' }).click()
  42 |       await form.getByLabel('已核对，未填写的扩展资料均为未知').check()
  43 |       await form.getByLabel('原因', { exact: true }).fill('Synthetic replacement reason'); await form.getByLabel('依据', { exact: true }).fill('Synthetic evidence')
  44 |       await extended.scrollIntoViewIfNeeded(); await maker.screenshot({ path: path.join(evidence, `${kind}-entry-desktop.png`) })
  45 |       const proposed = maker.waitForResponse(r => r.url().endsWith('/party-change/') && r.request().method() === 'POST')
  46 |       await form.getByRole('button', { name: '提交替换申请' }).click(); const proposalResponse = await proposed
  47 |       if (!proposalResponse.ok()) console.log('proposal error', kind, await proposalResponse.text())
  48 |       expect(proposalResponse.status()).toBe(201)
  49 |       const proposal = await proposalResponse.json()
  50 |       expect(proposal.proposed_snapshot.party_details[side].tax_id).toBe('')
  51 |       expect(proposal.proposed_snapshot.party_details[side].phone).toBeNull()
  52 |       await open(reviewer); const review = reviewer.locator('.document-party-versions'), diff = review.locator('.party-details-changes')
  53 |       await expect(diff).toContainText('Synthetic original billing'); await expect(diff).toContainText(`Synthetic new ${kind} billing`); await expect(diff).toContainText('未知 → 已留空')
  54 |       await diff.scrollIntoViewIfNeeded(); await reviewer.screenshot({ path: path.join(evidence, `${kind}-review-390.png`) })
  55 |       await maker.reload(); await maker.getByRole('button', { name: '查看主体版本与更正' }).click(); await maker.locator('.party-details-changes').scrollIntoViewIfNeeded(); await maker.screenshot({ path: path.join(evidence, `${kind}-review-desktop.png`) })
  56 |       await review.getByLabel('审批意见 / 处理原因').fill('Independent synthetic approval')
  57 |       const approved = reviewer.waitForResponse(r => r.url().includes('/approve/') && r.request().method() === 'POST')
  58 |       await review.getByRole('button', { name: '批准主体替换' }).click(); expect((await approved).status()).toBe(200)
  59 |       await review.getByRole('button', { name: '填写关联新单' }).click(); form = review.locator('.replacement-form')
  60 |       await form.getByLabel('单据日期').fill('2026-11-05'); await form.getByLabel('币种').fill('USD'); await form.getByLabel('汇率').fill('7.2')
  61 |       if (isOrder) { await form.getByLabel('运费').fill('0'); await form.getByLabel('折扣').fill('0'); await form.getByLabel('尾货策略').selectOption('SAME_CARTON') } else await form.getByLabel('付款计划').selectOption('none')
  62 |       await form.getByLabel('SKU').selectOption(String(f.sku)); await form.getByLabel('数量').fill('3'); await form.getByLabel('单价').fill('5'); await form.getByLabel('已核对全部新单资料和条款').check()
  63 |       const created = reviewer.waitForResponse(r => r.url().includes('/create-replacement/') && r.request().method() === 'POST')
  64 |       await form.getByRole('button', { name: '创建关联草稿' }).click(); const response = await created
  65 |       if (!response.ok()) console.log('creation error', kind, await response.text())
  66 |       expect(response.status()).toBe(200)
  67 |       const result = await response.json(), resultId = result[isOrder ? 'result_order_id' : 'result_purchase_order_id']
  68 |       const detailsResponse = await reviewer.request.get(`${api}/api/${route}/${resultId}/party-details/`); expect(detailsResponse.status()).toBe(200)
  69 |       const details = await detailsResponse.json(); console.log('RESULT DETAILS', kind, JSON.stringify(details))
  70 |       fs.writeFileSync(path.join(evidence, `${kind}-result-details.json`), JSON.stringify(details, null, 2))
  71 |       const party = details.details || details
  72 |       expect(party[side].tax_id).toBe(''); expect(party[side].phone).toBeNull(); expect(party[side].billing_address).toBe(`Synthetic new ${kind} billing`)
  73 |       logs.push({ kind, proposal: proposalResponse.status(), approval: 200, created: response.status(), resultId, proposalSnapshot: proposal.proposed_snapshot })
  74 |       await maker.close(); await reviewer.close()
  75 |     }
  76 |     const after = snapshot(); fs.writeFileSync(path.join(evidence, 'source-after.json'), JSON.stringify(after, null, 2)); expect(after).toEqual(before)
  77 |     fs.writeFileSync(path.join(evidence, 'http-results.json'), JSON.stringify(logs, null, 2))
  78 |   } finally { await a.close(); await b.close() }
  79 | })
  80 | 
```