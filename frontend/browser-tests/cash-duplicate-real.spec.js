import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { uploadBankVoucherViaApi, uploadBankVoucherThroughUi } from './helpers/bank-voucher.js'

test.use({ channel: 'chrome' })
const fixtureRoot = path.resolve('../docs/uat-evidence/r1-iss105-bank-duplicate-detection-20261103')
const report = process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
  ? path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'cash-duplicate')
  : fixtureRoot
const seed = path.resolve('../docs/uat-evidence/r1-iss105-independent-bank-fee-fix-20261103/seed_browser.py')
const screenshots = path.join(report, 'screenshots')
const results = []
let fixture

test.beforeAll(() => {
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  const result = spawnSync(process.env.ISOLATED_TEST_PYTHON, [seed], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
  expect(result.status, result.stderr).toBe(0)
  fixture = JSON.parse(result.stdout.trim().split('\n').at(-1))
  fs.mkdirSync(screenshots, { recursive: true })
})
test.afterAll(() => {
  fs.writeFileSync(path.join(report, 'browser-http.json'), JSON.stringify(results, null, 2))
  const inspect = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(fixtureRoot, 'inspect_browser.py')], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' })
  expect(inspect.status, inspect.stderr).toBe(0)
  const data = JSON.parse(inspect.stdout.trim().split('\n').at(-1))
  fs.writeFileSync(path.join(report, 'browser-database.json'), JSON.stringify(data, null, 2))
  expect(data.reviews).toHaveLength(2)
  expect(data.reviews.every(review => review.actor.kind === 'development_superadmin' && review.reason)).toBe(true)
})

for (const [index, width] of [1440, 390].entries()) {
  test(`核对同账户同额候选并有说明放行 ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    // Keep this deliberately duplicated pair distinct from the independent
    // bank-fee suite when both share the same isolated full-suite database.
    const date = index ? '2026-10-24' : '2026-10-23'
    const data = { event_no: `SYNTH-DUP-A-${width}`, request_key: `SYNTH-DUP-A-${width}`, kind: 'bank_fee', currency: 'CNY', direction: 'expense', bank_date: date, bank_net_amount: '5.00', fee_mode: 'none', fee_amount: '0', source_account: 'SYNTH_CNY', rmb_account: 'SYNTH_CNY', bank_reference: `SYNTH-REF-${width}`, bank_counterparty: '合成对手甲', bank_summary: '合成银行摘要甲', bank_transaction_id: `SYNTH-ID-${width}`, evidence_reference: 'SYNTH-VOUCHER', evidence_sha256: 'a'.repeat(64), evidence_note: '合成银行凭证', quoted_rate: '1', fee_for: null, correction_of: null, sources: [{ transaction_id: fixture.fee_ids[index * 2], amount: '5.00', verified: true }] }
    data.private_voucher = await uploadBankVoucherViaApi(page, data.sources.map(s => s.transaction_id))
    const first = await page.request.post('/api/rmb-cash-events/', { data })
    expect(first.status()).toBe(201)
    const firstId = (await first.json()).id
    expect((await page.request.post(`/api/rmb-cash-events/${firstId}/confirm/`, { data: { voucher_checked: true } })).status()).toBe(200)
    page.on('response', async response => {
      if (!response.url().includes('/api/rmb-cash-events/')) return
      try { results.push({ width, method: response.request().method(), path: new URL(response.url()).pathname, status: response.status(), response: await response.json() }) } catch {}
    })
    await page.goto('/rmb-cash-events', { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('button', { name: '新建资金事件' })).toBeVisible()
    await page.getByRole('button', { name: '新建资金事件' }).click()
    await page.getByLabel('事件类型').selectOption('bank_fee')
    await page.getByLabel('银行净额（CNY）').fill('5.00')
    await page.getByLabel('银行实际日期').fill(date)
    await page.getByLabel('来源银行账户标识').fill('SYNTH_CNY')
    await page.getByLabel('人民币账户标识').fill('SYNTH_CNY')
    await page.getByLabel('银行参考号').fill(`SYNTH-REF-B-${width}`)
    await page.getByLabel('交易对手').fill('合成对手乙')
    await page.getByLabel('银行摘要').fill('合成银行摘要乙')
    await page.getByLabel('银行交易标识').fill(`SYNTH-ID-B-${width}`)
    await page.getByLabel('凭证引用').fill('SYNTH-VOUCHER-B')
    await page.getByLabel('凭证 SHA256').fill('b'.repeat(64))
    await page.getByLabel('人工核实说明').fill('合成凭证核对')
    await page.locator('.source-option').filter({ hasText: fixture.fee_names[index * 2 + 1] }).getByRole('button', { name: '选择', exact: true }).click()
    await page.locator('.allocation-table input[type="number"]').fill('5.00')
    await page.locator('.verification-toggle input').check()
    await uploadBankVoucherThroughUi(page)
    await page.getByRole('button', { name: '预览' }).click()
    await expect(page.locator('.preview-box')).toBeVisible()
    await expect(page.locator('.warning-box').filter({ hasText: '疑似重复' })).toBeVisible()
    await page.getByRole('button', { name: '登记待确认草稿' }).click()
    await page.getByRole('checkbox', { name: /我已核对以上银行凭证/ }).check()
    await page.getByRole('button', { name: '确认银行凭证' }).click()
    const box = page.locator('section.warning-box').filter({ hasText: '疑似重复' })
    await expect(box).toContainText('合成对手甲')
    await expect(box).toContainText('合成银行摘要甲')
    await expect(box).toContainText(`SYNTH-ID-${width}`)
    await box.scrollIntoViewIfNeeded()
    await page.screenshot({ path: path.join(screenshots, `duplicate-review-${width}.png`) })
    await page.getByLabel('核实放行说明').fill('已逐项核对银行凭证，确认是另一笔交易')
    await page.getByRole('button', { name: '确认银行凭证' }).click()
    await expect(page.locator('.review-banner')).toContainText('已确认')
  })
}
