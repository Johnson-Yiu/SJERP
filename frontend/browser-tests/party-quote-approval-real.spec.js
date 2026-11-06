import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })

test('authenticated staff separately propose and approve a synthetic saved quote correction', async ({ browser, page, baseURL }) => {
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const root = path.resolve('../docs/uat-evidence/party-version-closeout-20261105')
  const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(root, 'seed_party_flow.py')], {
    cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  })
  expect(seed.status, seed.stderr).toBe(0)
  const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'party-approval')
  fs.mkdirSync(evidence, { recursive: true })
  const sent = await page.request.post(`/api/quotes/${fixture.id}/mark-sent/`)
  expect(sent.status()).toBe(200)
  const original = await (await page.request.get(`/api/quotes/${fixture.id}/`)).json()
  const apiBase = process.env.ISOLATED_PLAYWRIGHT_API_BASE_URL
  async function login(context, username) {
    const auth = await context.newPage()
    await auth.goto(`${apiBase}/admin/login/`)
    await auth.locator('[name="username"]').fill(username)
    await auth.locator('[name="password"]').fill('synthetic-only-password')
    await auth.locator('input[type="submit"]').click()
    await expect(auth).not.toHaveURL(/\/admin\/login/)
    await auth.close()
  }
  const a = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const b = await browser.newContext({ viewport: { width: 390, height: 844 } })
  try {
    await login(a, fixture.first_username)
    await login(b, fixture.second_username)
    const first = await a.newPage()
    const second = await b.newPage()
    const appUrl = new URL(`/quotes?detail=${fixture.id}`, baseURL).toString()
    await first.goto(appUrl)
    await first.getByRole('button', { name: '主体更正' }).click()
    await expect(first.locator('#party-address')).toBeVisible()
    await first.locator('#party-address').fill('Synthetic corrected address 123')
    await first.getByLabel('原因', { exact: true }).fill('Synthetic correction reason')
    await first.getByLabel('依据', { exact: true }).fill('Synthetic supporting evidence')
    await first.getByLabel('我已核对依据，确认法律主体未变').check()
    const submitted = first.waitForResponse(r => r.url().includes('/party-change/') && r.request().method() === 'POST')
    await first.getByRole('button', { name: '提交更正申请' }).click()
    expect((await submitted).status()).toBe(201)
    await expect(first.getByText('申请人不能审批自己的申请。')).toBeVisible()
    await first.getByText('申请人不能审批自己的申请。').scrollIntoViewIfNeeded()
    await first.screenshot({ path: path.join(evidence, 'request-desktop.png') })
    await second.goto(appUrl)
    await second.getByRole('button', { name: '主体更正' }).click()
    await second.getByLabel('审批意见').fill('Synthetic independent review')
    const approved = second.waitForResponse(r => r.url().includes('/approve/') && r.request().method() === 'POST')
    await second.getByRole('button', { name: '批准更正' }).click()
    expect((await approved).status()).toBe(200)
    await expect(second.getByText('Synthetic independent review')).toBeVisible()
    await second.getByText('Synthetic independent review').scrollIntoViewIfNeeded()
    await second.screenshot({ path: path.join(evidence, 'approved-390.png') })
    await first.reload()
    await first.getByRole('button', { name: '主体更正' }).click()
    const applied = first.waitForResponse(r => r.url().includes('/apply/') && r.request().method() === 'POST')
    await first.getByRole('button', { name: '生成报价草稿' }).click()
    const applyResponse = await applied
    expect(applyResponse.status()).toBe(200)
    const result = await applyResponse.json()
    const sourceResponse = await page.request.get(`/api/quotes/${fixture.id}/`)
    const childResponse = await page.request.get(`/api/quotes/${result.result_quote_id}/`)
    const source = await sourceResponse.json()
    const child = await childResponse.json()
    expect(source.buyer_address).toBe(original.buyer_address)
    expect(child.buyer_address).toBe('Synthetic corrected address 123')
    expect(child.status).toBe('draft')
    expect(child.total_amount).toBe(source.total_amount)
    for (const [name, id] of [['source', fixture.id], ['child', result.result_quote_id]]) {
      const file = await page.request.get(`/api/quotes/${id}/export/`)
      expect(file.status()).toBe(200)
      fs.writeFileSync(path.join(evidence, `synthetic-${name}.xlsx`), await file.body())
    }
    fs.writeFileSync(path.join(evidence, 'http-results.json'), JSON.stringify({ markSent: sent.status(), proposal: 201, approval: 200, apply: applyResponse.status(), source: sourceResponse.status(), child: childResponse.status(), firstUserId: fixture.first_id, reviewerUserId: fixture.second_id, sourceId: fixture.id, childId: result.result_quote_id, sourceAddress: source.buyer_address, childAddress: child.buyer_address, sourceTotal: source.total_amount, childTotal: child.total_amount }, null, 2))
  } finally {
    await a.close()
    await b.close()
  }
})
