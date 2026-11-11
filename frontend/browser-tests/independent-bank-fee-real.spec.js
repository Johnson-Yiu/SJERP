import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { uploadBankVoucherViaApi, uploadBankVoucherThroughUi } from './helpers/bank-voucher.js'

// Real Django + SQLite only: run through scripts/run-isolated-browser-tests.mjs.
test.use({ channel: 'chrome' })
const reportRoot = path.resolve('../docs/uat-evidence/r1-iss105-independent-bank-fee-fix-20261103')
const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT || reportRoot, 'independent-bank-fee')
const http = []
const layouts = []
let fixtures

test.beforeAll(() => {
  expect(process.env.ISOLATED_TEST_RUN_ID).toBeTruthy()
  expect(process.env.ISOLATED_TEST_DATABASE).toBeTruthy()
  const seed = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(reportRoot, 'seed_browser.py')], {
    cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  })
  expect(seed.status, seed.stderr || seed.stdout).toBe(0)
  fixtures = JSON.parse(seed.stdout.trim().split('\n').at(-1))
  fs.mkdirSync(path.join(evidence, 'screenshots'), { recursive: true })
  fs.writeFileSync(path.join(evidence, 'isolation-database.json'), JSON.stringify(fixtures, null, 2))
})
test.afterAll(() => {
  fs.mkdirSync(evidence, { recursive: true })
  fs.writeFileSync(path.join(evidence, 'http.json'), JSON.stringify(http, null, 2))
  fs.writeFileSync(path.join(evidence, 'layout.json'), JSON.stringify(layouts, null, 2))
  if (!fixtures) return
  const inspect = spawnSync(process.env.ISOLATED_TEST_PYTHON, [path.join(reportRoot, 'seed_browser.py'), JSON.stringify([...fixtures.fee_ids, fixtures.fx_id])], {
    cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8',
  })
  expect(inspect.status, inspect.stderr || inspect.stdout).toBe(0)
  const snapshot = JSON.parse(inspect.stdout.trim().split('\n').at(-1))
  fs.writeFileSync(path.join(evidence, 'database-after.json'), JSON.stringify(snapshot, null, 2))
  expect(snapshot.source_rows).toEqual(fixtures.source_rows)
})

for (const [index, width] of [1440, 390].entries()) {
  test(`independent fee without FX parent: real UI ${width}px`, async ({ page }) => {
    test.setTimeout(120000)
    await page.setViewportSize({ width, height: 960 })
    const before = await (await page.request.get('/api/actual-rmb-cash/?date_from=2026-10-01&date_to=2026-10-31')).json()
    page.on('response', async response => {
      if (!response.url().includes('/api/rmb-cash-events/')) return
      let result
      try { result = await response.json() } catch { return }
      http.push({ width, method: response.request().method(), path: new URL(response.url()).pathname,
        status: response.status(), request: response.request().postDataJSON(), result })
    })
    await page.goto('/rmb-cash-events')
    await page.getByRole('button', { name: '新增资金事件' }).click()
    const parent = page.getByLabel('关联结汇事件（可选）')
    const fillBankInputs = async () => {
      await page.getByLabel('事件类型').selectOption('bank_fee')
      await expect(parent).toHaveValue('')
      await expect(parent).not.toHaveAttribute('required', '')
      await page.getByLabel('银行净额（CNY）').fill('5.00')
      await page.getByLabel('实际到账日期').fill(index ? '2026-10-19' : '2026-10-18')
      await page.getByRole('combobox', { name: '来源账户', exact: true }).selectOption('SYNTH_CNY')
      await page.getByRole('combobox', { name: '人民币账户', exact: true }).selectOption('SYNTH_CNY')
      await page.getByLabel('银行参考号').fill(`SYNTH-INDEPENDENT-${width}`)
    }
    await fillBankInputs()
    await page.reload()
    await page.getByRole('button', { name: '新增资金事件' }).click()
    await expect(page.getByLabel('银行参考号')).toHaveValue('')
    await fillBankInputs()
    await expect(parent).toHaveValue('')
    await page.getByLabel('核对说明').fill('合成银行手续费凭证；隔离测试人工核实。')
    await page.locator('.source-option').filter({ hasText: fixtures.fee_names[index] }).getByRole('button', { name: '选择', exact: true }).click()
    await page.locator('.allocation-table input[type="number"]').fill('5.00')
    // A real client refusal retains the form; correct it and retry the real API.
    await page.getByRole('button', { name: '预览结汇信息' }).click()
    await expect(page.getByRole('alert')).toContainText('逐条核实')
    await page.locator('.verification-toggle input').check()
    await page.getByLabel('银行净额（CNY）').fill('6.00')
    const refused = page.waitForResponse(r => r.url().endsWith('/rmb-cash-events/preview/') && r.request().method() === 'POST')
    await page.getByRole('button', { name: '预览结汇信息' }).click()
    expect((await refused).status()).toBe(400)
    await expect(page.getByRole('alert')).toBeVisible()
    await page.getByLabel('银行净额（CNY）').fill('5.00')
    await uploadBankVoucherThroughUi(page)
    const previewResponse = page.waitForResponse(r => r.url().endsWith('/rmb-cash-events/preview/') && r.request().method() === 'POST')
    await page.getByRole('button', { name: '预览结汇信息' }).click()
    const preview = await previewResponse
    expect(preview.status()).toBe(200)
    const previewPayload = preview.request().postDataJSON()
    expect(previewPayload.fee_for).toBeNull()
    expect(previewPayload.request_key).toBeTruthy()
    await expect(page.locator('.preview-box')).toBeVisible()
    await parent.scrollIntoViewIfNeeded()
    const bounds = await parent.boundingBox()
    expect(bounds.x).toBeGreaterThanOrEqual(0)
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width)
    layouts.push({ width, chrome: page.context().browser().version(), parentSelect: bounds, selection: await parent.inputValue(), required: await parent.getAttribute('required') })
    await page.screenshot({ path: path.join(evidence, 'screenshots', `optional-fee-${width}.png`) })
    const registered = page.waitForResponse(r => r.url().endsWith('/rmb-cash-events/') && r.request().method() === 'POST')
    await page.getByRole('button', { name: '登记待确认结汇' }).click()
    const registeredResponse = await registered
    expect(registeredResponse.request().postDataJSON().request_key).toBe(previewPayload.request_key)
    const created = await registeredResponse.json()
    expect(created.fee_for).toBeNull()
    await expect(page.getByRole('button', { name: '确认银行凭证' })).toBeDisabled()
    await page.getByRole('checkbox', { name: /我已核对银行凭证/ }).check()
    await page.getByRole('button', { name: '确认银行凭证' }).click()
    await expect(page.locator('.review-banner')).toContainText('已确认')
    const proofWidth = await page.locator('.private-bank-proof').evaluate(el => ({ content: el.scrollWidth, width: el.clientWidth }))
    expect(proofWidth.content).toBeLessThanOrEqual(proofWidth.width)
    await page.locator('.review-banner').scrollIntoViewIfNeeded()
    await page.locator('.private-bank-proof').scrollIntoViewIfNeeded()
    await page.screenshot({ path: path.join(evidence, 'screenshots', `confirmed-fee-${width}.png`) })
    const replay = await page.request.post(`/api/rmb-cash-events/${created.id}/confirm/`, { data: { voucher_checked: true } })
    expect(replay.status()).toBe(200)
    http.push({ width, method: 'POST', path: `/api/rmb-cash-events/${created.id}/confirm/`, request: { voucher_checked: true }, status: replay.status(), result: await replay.json(), replay: true })
    const report = await page.request.get('/api/actual-rmb-cash/?date_from=2026-10-01&date_to=2026-10-31')
    const result = await report.json()
    expect(result.totals.count).toBe(before.totals.count + 1)
    expect(Number(result.totals.outflow)).toBe(Number(before.totals.outflow) + 5)
    expect(Number(result.totals.inflow)).toBe(Number(before.totals.inflow))
    http.push({ width, path: '/api/actual-rmb-cash/', status: report.status(), result })
    await page.reload()
    await expect(page.locator('.cash-row').filter({ hasText: created.event_no })).toContainText('已确认')
  })
}

test('real API preserves optional-parent rejection, source quota and idempotency protections', async ({ page }) => {
  const privateProofs = new Map()
  const call = async (suffix, data, expected) => {
    if (!suffix && data.sources) {
      const ids = data.sources.map(s => s.transaction_id).sort((a, b) => a - b)
      const key = JSON.stringify(ids)
      if (!privateProofs.has(key)) privateProofs.set(key, await uploadBankVoucherViaApi(page, ids))
      data = { ...data, private_voucher: privateProofs.get(key) }
    }
    const response = await page.request.post('/api/rmb-cash-events/' + suffix, { data })
    const result = await response.json()
    http.push({ method: 'POST', path: '/api/rmb-cash-events/' + suffix, request: data, status: response.status(), result })
    expect(response.status(), JSON.stringify(result)).toBe(expected)
    return result
  }
  const base = {
    event_no: fixtures.prefix + '-PARENT', request_key: fixtures.prefix + '-PARENT',
    kind: 'fx_settlement', currency: 'USD', direction: 'income', bank_date: '2026-10-18',
    bank_net_amount: '700.00', fee_mode: 'none', fee_amount: '0', quoted_rate: '7',
    source_account: 'SYNTH_FX', rmb_account: 'SYNTH_CNY', bank_reference: fixtures.prefix + '-FX',
    evidence_reference: fixtures.prefix + '-VOUCHER', evidence_sha256: 'b'.repeat(64), evidence_note: '合成凭证人工核实',
    sources: [{ transaction_id: fixtures.fx_id, amount: '100.00', verified: true }],
    fee_for: null, correction_of: null,
  }
  const parent = await call('', base, 201)
  const fee = { ...base, kind: 'bank_fee', currency: 'CNY', direction: 'expense', bank_net_amount: '5.00', quoted_rate: '1',
    bank_date: '2026-10-20',
    source_account: 'SYNTH_CNY', request_key: fixtures.prefix + '-LINKED', event_no: fixtures.prefix + '-LINKED',
    fee_for: parent.id, sources: [{ transaction_id: fixtures.fee_ids[2], amount: '5.00', verified: true }] }
  await call('preview/', fee, 400) // Parent pending.
  await call(parent.id + '/confirm/', { voucher_checked: true }, 200)
  await call('preview/', { ...fee, fee_for: 999999999 }, 404)
  await call('preview/', { ...fee, rmb_account: 'WRONG' }, 400)
  const before = await (await page.request.get('/api/rmb-cash-events/')).json()
  await call('', { ...fee, sources: [{ transaction_id: fixtures.fx_id, amount: '5.00', verified: true }] }, 400)
  expect((await (await page.request.get('/api/rmb-cash-events/')).json()).results.length).toBe(before.results.length)
  await call('preview/', fee, 200)
  const linked = await call('', fee, 201)
  await call(linked.id + '/confirm/', { voucher_checked: true }, 200)
  await call(linked.id + '/confirm/', { voucher_checked: true }, 200)
  const same = await call('', fee, 200)
  expect(same.id).toBe(linked.id)
  await call('', { ...fee, request_key: fixtures.prefix + '-OVER', event_no: fixtures.prefix + '-OVER' }, 409)
  // A standalone fee event is not itself a valid FX parent.
  await call('preview/', { ...fee, fee_for: linked.id, sources: [{ transaction_id: fixtures.fee_ids[3], amount: '5.00', verified: true }] }, 400)
  const included = await call('', { ...base, event_no: fixtures.prefix + '-INCLUDED', request_key: fixtures.prefix + '-INCLUDED',
    bank_net_amount: '695.00', fee_mode: 'included', fee_amount: '5.00' }, 201)
  await call(included.id + '/confirm/', { voucher_checked: true }, 200)
  await call('preview/', { ...fee, fee_for: included.id, sources: [{ transaction_id: fixtures.fee_ids[3], amount: '5.00', verified: true }] }, 400)
})
