import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })

test('formal SO and PO corrections retain original snapshots and business facts', async ({ browser, page, baseURL }) => {
  test.setTimeout(120000)
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const root = path.resolve('../docs/uat-evidence/party-version-closeout-02')
  const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(root, 'seed_document_party.py')], {
    cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  })
  expect(seed.status, seed.stderr).toBe(0)
  const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'document-party')
  fs.mkdirSync(evidence, { recursive: true })
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
    await login(a, fixture.first_username); await login(b, fixture.second_username)
    const first = await a.newPage(), second = await b.newPage(), results = []
    for (const [kind, route, id, snapshotField] of [['order', 'orders', fixture.order, 'customer_address_snapshot'], ['purchase', 'purchase-orders', fixture.purchase, 'supplier_address_snapshot']]) {
      const before = await (await page.request.get(`/api/${route}/${id}/`)).json()
      const url = new URL(`/${route}?detail=${id}`, baseURL).toString()
      async function open(p) {
        await p.goto(url, { waitUntil: 'domcontentloaded' })
        await p.getByRole('button', { name: '查看主体版本与更正' }).click()
        await expect(p.locator('.document-party-versions')).toContainText('当前有效主体资料')
      }
      await open(first)
      const panel = first.locator('.document-party-versions')
      await panel.getByLabel('地址', { exact: true }).fill(`Synthetic corrected ${kind} address`)
      await panel.getByLabel('原因', { exact: true }).fill('Synthetic reason')
      await panel.getByLabel('依据', { exact: true }).fill('Synthetic evidence')
      await panel.getByLabel('已核对依据，确认法律主体未变').check()
      const proposal = first.waitForResponse(r => r.url().endsWith('/party-change/') && r.request().method() === 'POST')
      await panel.getByRole('button', { name: '提交更正申请' }).click()
      expect((await proposal).status()).toBe(201)
      await open(second)
      const review = second.locator('.document-party-versions')
      await review.getByLabel('审批意见 / 处理原因').fill('Independent synthetic review')
      const approval = second.waitForResponse(r => r.url().includes('/approve/') && r.request().method() === 'POST')
      await review.getByRole('button', { name: '批准更正' }).click()
      expect((await approval).status()).toBe(200)
      await expect(review.getByText('已批准', { exact: false }).first()).toBeVisible()
      const applied = second.waitForResponse(r => r.url().includes('/apply/') && r.request().method() === 'POST')
      await review.getByRole('button', { name: '生效主体更正' }).click()
      expect((await applied).status()).toBe(200)
      await expect(review).toContainText(`Synthetic corrected ${kind} address`)
      await review.getByText(`Synthetic corrected ${kind} address`).first().scrollIntoViewIfNeeded()
      await second.screenshot({ path: path.join(evidence, `${kind}-390.png`) })
      await first.reload(); await first.getByRole('button', { name: '查看主体版本与更正' }).click()
      await expect(first.locator('.document-party-versions')).toContainText(`Synthetic corrected ${kind} address`)
      await first.locator('.document-party-versions').scrollIntoViewIfNeeded()
      await first.screenshot({ path: path.join(evidence, `${kind}-desktop.png`) })
      const afterResponse = await page.request.get(`/api/${route}/${id}/`)
      const after = await afterResponse.json()
      expect(after.effective_party.address).toBe(`Synthetic corrected ${kind} address`)
      expect(after[snapshotField]).toBe(before[snapshotField])
      expect(after.total_amount).toBe(before.total_amount)
      expect(after.items).toEqual(before.items)
      results.push({ kind, id, get: afterResponse.status(), proposal: 201, approval: 200, apply: 200, originalAddress: after[snapshotField], total: after.total_amount })
    }
    fs.writeFileSync(path.join(evidence, 'http-results.json'), JSON.stringify(results, null, 2))
  } finally { await a.close(); await b.close() }
})
