import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome' })

test('two authenticated staff reject, reapply and withdraw with saved history', async ({ browser, page, baseURL }) => {
  test.setTimeout(90000)
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const root = path.resolve('../docs/uat-evidence/party-version-closeout-20261105')
  const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(root, 'seed_party_flow.py')], {
    cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  })
  expect(seed.status, seed.stderr).toBe(0)
  const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'lifecycle')
  fs.mkdirSync(evidence, { recursive: true })
  expect((await page.request.post(`/api/quotes/${fixture.id}/mark-sent/`)).status()).toBe(200)
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
  const requester = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const reviewer = await browser.newContext({ viewport: { width: 390, height: 844 } })
  try {
    await login(requester, fixture.first_username)
    await login(reviewer, fixture.second_username)
    const first = await requester.newPage()
    const second = await reviewer.newPage()
    const url = new URL(`/quotes?detail=${fixture.id}`, baseURL).toString()
    async function open(p) {
      await p.goto(url)
      await p.getByRole('button', { name: '主体更正' }).click()
      await expect(p.locator('#party-address')).toBeVisible()
    }
    async function propose(p, address) {
      await p.locator('#party-address').fill(address)
      await p.getByLabel('原因', { exact: true }).fill('Synthetic correction reason')
      await p.getByLabel('依据', { exact: true }).fill('Synthetic supporting evidence')
      await p.getByLabel('我已核对依据，确认法律主体未变').check()
      const response = p.waitForResponse(r => r.url().endsWith('/party-change/') && r.request().method() === 'POST')
      await p.getByRole('button', { name: '提交更正申请' }).click()
      expect((await response).status()).toBe(201)
      await expect(p.getByText('申请人不能审批自己的申请。')).toBeVisible()
    }
    await open(first)
    await propose(first, 'Synthetic correction A')
    await open(second)
    await second.getByLabel('处理原因').fill('Synthetic independent rejection')
    const denied = second.waitForResponse(r => r.url().includes('/reject/') && r.request().method() === 'POST')
    await second.getByRole('button', { name: '拒绝申请' }).click()
    expect((await denied).status()).toBe(200)
    await expect(second.getByText(/Synthetic independent rejection/)).toBeVisible()
    await second.getByText(/Synthetic independent rejection/).scrollIntoViewIfNeeded()
    await second.screenshot({ path: path.join(evidence, 'rejected-390.png') })
    await first.reload()
    await first.getByRole('button', { name: '主体更正' }).click()
    await propose(first, 'Synthetic correction B')
    const pending = first.locator('.party-request').filter({ hasText: 'Synthetic correction B' })
    await pending.getByLabel('处理原因').fill('Synthetic withdrawal')
    const withdrawn = first.waitForResponse(r => r.url().includes('/withdraw/') && r.request().method() === 'POST')
    await pending.getByRole('button', { name: '撤回申请' }).click()
    expect((await withdrawn).status()).toBe(200)
    await expect(first.getByText(/Synthetic withdrawal/)).toBeVisible()
    await first.getByText(/Synthetic withdrawal/).scrollIntoViewIfNeeded()
    await first.screenshot({ path: path.join(evidence, 'withdrawn-desktop.png') })
    const historyResponse = await first.request.get(`${apiBase}/api/quotes/${fixture.id}/party-change/`)
    expect(historyResponse.status()).toBe(200)
    const history = await historyResponse.json()
    expect(history.requests.map(item => item.status).sort()).toEqual(['rejected', 'withdrawn'])
    fs.writeFileSync(path.join(evidence, 'http-results.json'), JSON.stringify({ quoteId: fixture.id,
      requester: fixture.first_id, reviewer: fixture.second_id, reject: 200, withdraw: 200,
      status: history.requests.map(item => ({ id: item.id, status: item.status, actor: item.terminal_event.actor_id })) }, null, 2))
  } finally {
    await requester.close()
    await reviewer.close()
  }
})
