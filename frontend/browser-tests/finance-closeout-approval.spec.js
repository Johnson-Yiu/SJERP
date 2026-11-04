import { test, expect } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { syntheticVoucherPdf } from './helpers/bank-voucher.js'

test.use({ channel: 'chrome' })
const root = process.env.FINANCE_CLOSEOUT_EVIDENCE || '../docs/uat-evidence/finance-closeout-batch-20261104/browser'

for (const width of [1440, 390]) test(`authenticated finance closure and reconciliation ${width}px`, async ({ page, context, baseURL }) => {
  test.setTimeout(120000) // Real multi-account approval, posting and file workflow.
  await fs.mkdir(root, { recursive: true })
  const identities = JSON.parse(await fs.readFile(path.join(process.env.FINANCE_AUTH_EVIDENCE_DIR, 'fixture.json'), 'utf8'))
  const csrf = 'a'.repeat(32)
  const coreSnapshot = () => JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, ['../docs/uat-evidence/finance-closeout-batch-20261104/seed_finance_browser.py', '--snapshot'], { encoding: 'utf8', env: process.env }).trim())
  const legacyBefore = coreSnapshot()
  const records = []
  const signIn = async role => {
    await context.clearCookies()
    await context.addCookies([{ name: 'sessionid', value: identities[role].session, url: baseURL, httpOnly: true, sameSite: 'Lax' }, { name: 'csrftoken', value: csrf, url: baseURL, sameSite: 'Lax' }])
  }
  const call = async (action, data, status = 200) => {
    const response = await page.request.post(`/api/finance-ledger/${action}/`, { data, headers: { 'X-CSRFToken': csrf } })
    const body = await response.json()
    records.push({ action, request: data, status: response.status(), body })
    await fs.writeFile(path.join(root, `authenticated-http-progress-${width}.json`), JSON.stringify(records, null, 2))
    expect(response.status(), JSON.stringify(body)).toBe(status)
    return body
  }
  await page.setViewportSize({ width, height: 1050 })
  await signIn('maker')
  const suffix = `${width}-${Date.now()}`
  const bank = await call('accounts', { code: `SYNTH-AUTH-B-${suffix}`, name: `合成核对银行-${width}`, account_type: 'bank', ownership: 'own', ownership_reason: '合成开户凭证' }, 201)
  const cash = await call('accounts', { code: `SYNTH-AUTH-C-${suffix}`, name: `合成核对现金-${width}`, account_type: 'cash', ownership: 'own', ownership_reason: '合成现金盘点凭证' }, 201)
  const proofResponse = await page.request.post('/api/finance-ledger/vouchers/', { headers: { 'X-CSRFToken': csrf }, multipart: { file: { name: `synthetic-auth-${width}.pdf`, mimeType: 'application/pdf', buffer: syntheticVoucherPdf() } } })
  expect(proofResponse.status()).toBe(201)
  const proof = await proofResponse.json()
  const make = async changes => {
    const key = `SYNTH-AUTH-${suffix}-${records.length}`
    return call('instructions', { request_key: key, source_system: 'SYNTH-AUTH-CHROME', source_key: key,
      kind: 'cash', account: bank.id, actual_date: '2026-02-02', amount: '100.00', direction: 'income',
      nature: 'unclassified', truth: 'verified', voucher: proof.id, reason: '合成资料逐项核实', ...changes }, 201)
  }
  const post = obj => call('post', { id: obj.id, voucher_checked: true })
  const approve = async obj => { await signIn('reviewer'); const result = await call('approve', { id: obj.id }); await signIn('maker'); return result }
  const opening = await make({ kind: 'opening', actual_date: '2026-02-01', amount: '1000.00' })
  await call('approve', { id: opening.id }, 400)
  await call('post', { id: opening.id, voucher_checked: true }, 400)
  await signIn('reviewer')
  await page.goto('/finance-ledger')
  await page.getByRole('button', { name: '登记与复核', exact: true }).click()
  const openingCard = page.locator('article').filter({ hasText: `指令 #${opening.id} ·` })
  const approvalResponse = page.waitForResponse(r => r.url().endsWith('/api/finance-ledger/approve/') && r.request().method() === 'POST')
  await openingCard.getByRole('button', { name: '另一人复核', exact: true }).click()
  const approvedHttp = await approvalResponse
  const approvedBody = await approvedHttp.json()
  records.push({ action: 'approve-via-ui', status: approvedHttp.status(), body: approvedBody })
  await fs.writeFile(path.join(root, `authenticated-http-progress-${width}.json`), JSON.stringify(records, null, 2))
  expect(approvedHttp.status(), JSON.stringify(approvedBody)).toBe(200)
  await expect(openingCard).toContainText('已复核')
  await signIn('maker')
  await post(opening)
  const receipt = await post(await make({ amount: '100.00' }))
  const correction = await make({ kind: 'correction', parent: receipt.id, direction: 'income', amount: '90.00', nature: 'correction', actual_date: '2026-02-03' })
  await approve(correction); const corrected = await post(correction)
  const refundApproval = await make({ kind: 'refund_approval', parent: corrected.id, direction: 'expense', amount: '150.00', excess_reason: '按已核实90元收款批准额外赔偿60元' })
  await approve(refundApproval)
  await call('post', { id: refundApproval.id, voucher_checked: true }, 400)
  const refund = await make({ kind: 'refund_payment', approval: refundApproval.id, direction: 'expense', amount: '150.00', nature: 'commercial_refund', actual_date: '2026-02-04' })
  await approve(refund)
  const paid = await post(refund)
  expect(paid.refund_excess_amount).toBe('60.00')
  await post(await make({ kind: 'refund_return', parent: paid.id, amount: '50.00', actual_date: '2026-02-05' }))
  const out = await post(await make({ direction: 'expense', amount: '40.00', nature: 'internal_principal', actual_date: '2026-02-06' }))
  const inc = await post(await make({ account: cash.id, amount: '40.00', nature: 'internal_principal', actual_date: '2026-02-07' }))
  await call('transfers', { outgoing: out.id, incoming: inc.id, reason: '合成跨日两端真实凭证核实' }, 201)
  await call('classifications', { fact: corrected.id, nature: 'interest', reason: '合成利息核实' }, 201)
  await call('reviews', { account: bank.id, date_from: '2026-02-01', date_to: '2026-02-28', voucher: proof.id, statement_balance: '950.00', completed: true, reason: '合成银行月末核对' }, 201)
  await page.goto('/finance-ledger')
  await page.getByRole('button', { name: '账户核对', exact: true }).click()
  await expect(page.locator('article').filter({ hasText: `账户 #${bank.id} ·` })).toContainText('核对完成')
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: path.join(root, `reconciliation-completed-${width}.png`), fullPage: true })
  await post(await make({ actual_date: '2026-02-08', amount: '1.00', nature: 'interest' }))
  await page.getByRole('button', { name: '刷新', exact: true }).click()
  await expect(page.locator('article').filter({ hasText: `账户 #${bank.id} ·` })).toContainText('需重新核对')
  await page.screenshot({ path: path.join(root, `reconciliation-reopened-${width}.png`), fullPage: true })
  const snapshot = coreSnapshot()
  expect(snapshot).toEqual(legacyBefore)
  const csv = await page.request.get('/api/finance-ledger/facts/?date_from=2026-02-01&date_to=2026-02-28&export=csv')
  expect(csv.status()).toBe(200)
  await fs.writeFile(path.join(root, `authenticated-facts-${width}.csv`), await csv.body())
  const actual = await page.request.get('/api/actual-rmb-cash/?date_from=2026-02-01&date_to=2026-02-28')
  expect(actual.status()).toBe(200)
  const actualBody = await actual.json()
  expect(actualBody.events.some(e => e.id === -paid.id && e.refund_excess_amount === '60.00')).toBe(true)
  expect(actualBody.events.some(e => e.id === -out.id || e.id === -inc.id)).toBe(false)
  expect(actualBody.by_account_type.map(r => r.account_type)).toEqual(['bank', 'cash'])
  const downloaded = await page.request.get(`/api/finance-ledger/voucher-download/?id=${proof.id}`)
  expect(downloaded.status()).toBe(200)
  expect(downloaded.headers()['cache-control']).toBe('private, no-store')
  await fs.writeFile(path.join(root, `synthetic-voucher-${width}.pdf`), await downloaded.body())
  await fs.writeFile(path.join(root, `authenticated-http-${width}.json`), JSON.stringify({ records, actual: actualBody, core_tables_before: legacyBefore, core_tables_after: snapshot }, null, 2))
})
