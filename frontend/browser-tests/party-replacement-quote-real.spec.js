import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome', viewport: { width: 390, height: 844 } })
test('synthetic quote replacement uses independent approval and synthetic saved template', async ({ browser, baseURL }) => {
  test.setTimeout(180000)
  const root = path.resolve('../docs/uat-evidence/party-version-closeout-02')
  const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(root, 'seed_replacement_quote_browser.py')], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
  expect(seed.status, seed.stderr).toBe(0)
  const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'replacement-quote')
  fs.mkdirSync(evidence, { recursive: true })
  const apiBase = process.env.ISOLATED_PLAYWRIGHT_API_BASE_URL
  const a = await browser.newContext({ viewport: { width: 1440, height: 900 } }), b = await browser.newContext({ viewport: { width: 390, height: 844 } })
  async function login(context, username) {
    const p = await context.newPage(); await p.goto(`${apiBase}/admin/login/`)
    await p.locator('[name="username"]').fill(username); await p.locator('[name="password"]').fill('synthetic-only-password')
    await p.locator('input[type="submit"]').click(); await expect(p).not.toHaveURL(/\/admin\/login/); await p.close()
  }
  async function open(context) {
    const p = await context.newPage(); await p.goto(new URL(`/quotes?detail=${fixture.quote}`, baseURL).toString())
    await p.getByRole('button', { name: '主体更正' }).click()
    await expect(p.locator('.party-change-panel')).toContainText('主体变更申请')
    return p
  }
  try {
    await login(a, fixture.first_username); await login(b, fixture.second_username)
    const maker = await open(a), panel = maker.locator('.party-change-panel')
    await panel.locator('.party-change-type select').selectOption('replacement')
    const form = panel.locator('.replacement-form')
    await form.getByLabel('目标客户').selectOption(String(fixture.target))
    while (await form.getByRole('button', { name: '确认留空' }).count()) await form.getByRole('button', { name: '确认留空' }).first().click()
    await form.getByLabel('原因').fill('Synthetic replacement'); await form.getByLabel('依据').fill('Synthetic evidence')
    const proposed = maker.waitForResponse(r => r.url().endsWith('/party-change/') && r.request().method() === 'POST')
    await form.getByRole('button', { name: '提交替换申请' }).click(); expect((await proposed).status()).toBe(201)
    const reviewer = await open(b), review = reviewer.locator('.party-change-panel')
    await review.locator('.party-request').first().scrollIntoViewIfNeeded(); await reviewer.screenshot({ path: path.join(evidence, 'review-390.png') })
    await maker.reload(); await maker.getByRole('button', { name: '主体更正' }).click(); await maker.locator('.party-request').first().scrollIntoViewIfNeeded(); await maker.screenshot({ path: path.join(evidence, 'review-desktop.png') })
    await review.locator('.party-request .party-approval-note input').first().fill('Synthetic independent review')
    const approved = reviewer.waitForResponse(r => r.url().includes('/approve/') && r.request().method() === 'POST')
    await review.getByRole('button', { name: '批准主体替换记录' }).click(); expect((await approved).status()).toBe(200)
    await review.getByRole('button', { name: '填写关联新单' }).click()
    const draft = review.locator('.replacement-form')
    await draft.getByLabel('单据日期').fill('2026-11-05'); await draft.getByLabel('币种').fill('USD'); await draft.getByLabel('汇率').fill('7.2')
    await draft.getByLabel('运费').fill('0'); await draft.getByLabel('折扣').fill('0'); await draft.getByLabel('定金比例').fill('0.3')
    await draft.getByLabel('SKU').selectOption(String(fixture.sku)); await draft.getByLabel('数量').fill('3'); await draft.getByLabel('单价').fill('5')
    await draft.getByLabel('已核对全部新单资料和条款').check()
    await draft.scrollIntoViewIfNeeded(); await reviewer.screenshot({ path: path.join(evidence, 'new-draft-390.png') })
    const created = reviewer.waitForResponse(r => r.url().includes('/create-replacement/') && r.request().method() === 'POST')
    await draft.getByRole('button', { name: '创建关联草稿' }).click()
    const response = await created
    if (!response.ok()) console.error('Replacement creation response:', response.status(), await response.text())
    expect(response.status()).toBe(200)
    const result = await response.json(); expect(result.result_quote_id).toBeTruthy()
    const saved = await (await reviewer.request.get(`${apiBase}/api/quotes/${result.result_quote_id}/`)).json()
    expect(saved.status).toBe('draft'); expect(saved.customer).toBe(fixture.target)
    expect(saved.buyer_country_snapshot).toBe('')
    const pi = await reviewer.request.get(`${apiBase}/api/quotes/${result.result_quote_id}/pi-data/`)
    expect(pi.status()).toBe(200); expect((await pi.json()).seller.name).toBe('Synthetic Seller')
    fs.writeFileSync(path.join(evidence, 'http-results.json'), JSON.stringify({ proposal: 201, approval: 200, created: response.status(), pi: pi.status(), result_quote_id: result.result_quote_id }, null, 2))
  } finally { await a.close(); await b.close() }
})
