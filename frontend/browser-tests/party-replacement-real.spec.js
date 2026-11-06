import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

test.use({ channel: 'chrome', viewport: { width: 390, height: 844 } })
test('synthetic order replacement uses independent approval and explicit new draft', async ({ browser, baseURL }) => {
  test.setTimeout(120000)
  const root = path.resolve('../docs/uat-evidence/party-version-closeout-02')
  const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(root, 'seed_replacement_browser.py')], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
  expect(seed.status, seed.stderr).toBe(0)
  const fixture = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'replacement')
  fs.mkdirSync(evidence, { recursive: true })
  const apiBase = process.env.ISOLATED_PLAYWRIGHT_API_BASE_URL
  const a = await browser.newContext({ viewport: { width: 390, height: 844 } })
  const b = await browser.newContext({ viewport: { width: 390, height: 844 } })
  async function login(context, username) {
    const p = await context.newPage(); await p.goto(`${apiBase}/admin/login/`)
    await p.locator('[name="username"]').fill(username); await p.locator('[name="password"]').fill('synthetic-only-password')
    await p.locator('input[type="submit"]').click(); await expect(p).not.toHaveURL(/\/admin\/login/); await p.close()
  }
  async function open(context) {
    const p = await context.newPage(); await p.goto(new URL(`/orders?detail=${fixture.order}`, baseURL).toString())
    await p.getByRole('button', { name: '查看主体版本与更正' }).click()
    await expect(p.locator('.document-party-versions')).toContainText('当前有效主体资料')
    return p
  }
  try {
    await login(a, fixture.first_username); await login(b, fixture.second_username)
    const maker = await open(a), panel = maker.locator('.document-party-versions')
    await panel.getByRole('button', { name: '申请更换法律主体' }).click()
    const form = panel.locator('.replacement-form')
    await form.getByLabel('目标客户').selectOption(String(fixture.replacement_customer))
    while (await form.getByRole('button', { name: '确认留空' }).count()) await form.getByRole('button', { name: '确认留空' }).first().click()
    await form.getByLabel('原因').fill('Synthetic replacement reason'); await form.getByLabel('依据').fill('Synthetic evidence')
    await form.scrollIntoViewIfNeeded(); await maker.screenshot({ path: path.join(evidence, 'proposal-390.png') })
    const proposed = maker.waitForResponse(r => r.url().endsWith('/party-change/') && r.request().method() === 'POST')
    await form.getByRole('button', { name: '提交替换申请' }).click(); expect((await proposed).status()).toBe(201)
    const reviewer = await open(b), review = reviewer.locator('.document-party-versions')
    await review.getByLabel('审批意见 / 处理原因').fill('Synthetic independent review')
    const approved = reviewer.waitForResponse(r => r.url().includes('/approve/') && r.request().method() === 'POST')
    await review.getByRole('button', { name: '批准主体替换' }).click(); expect((await approved).status()).toBe(200)
    await review.getByRole('button', { name: '填写关联新单' }).click()
    const newForm = review.locator('.replacement-form')
    await newForm.getByLabel('单据日期').fill('2026-11-05'); await newForm.getByLabel('币种').fill('USD'); await newForm.getByLabel('汇率').fill('7.2')
    await newForm.getByLabel('运费').fill('0'); await newForm.getByLabel('折扣').fill('0'); await newForm.getByLabel('尾货策略').selectOption('SAME_CARTON')
    await newForm.getByLabel('SKU').selectOption(String(fixture.sku)); await newForm.getByLabel('数量').fill('3'); await newForm.getByLabel('单价').fill('5')
    await newForm.getByLabel('已核对全部新单资料和条款').check()
    await newForm.scrollIntoViewIfNeeded(); await reviewer.screenshot({ path: path.join(evidence, 'new-draft-390.png') })
    const created = reviewer.waitForResponse(r => r.url().includes('/create-replacement/') && r.request().method() === 'POST')
    await newForm.getByRole('button', { name: '创建关联草稿' }).click()
    const response = await created; expect(response.status()).toBe(200)
    const result = await response.json(); expect(result.result_order_id).toBeTruthy()
    const saved = await (await reviewer.request.get(`${apiBase}/api/orders/${result.result_order_id}/`)).json()
    expect(saved.status).toBe('draft'); expect(saved.customer).toBe(fixture.replacement_customer)
    expect(saved.items).toHaveLength(1); expect(saved.items[0].quantity).toBe('3.00')
    fs.writeFileSync(path.join(evidence, 'http-results.json'), JSON.stringify({ proposal: 201, approval: 200, created: response.status(), result_order_id: result.result_order_id }, null, 2))
  } finally { await a.close(); await b.close() }
})
