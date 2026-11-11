import { test, expect } from '@playwright/test'
import { syntheticVoucherPdf } from './helpers/bank-voucher.js'

// MOCKED_TEST: UI sequencing and stable-key presentation; real database/browser evidence is kept in the P2-B evidence folder.
test('cash event UI previews, registers, and confirms without changing receipt flows', async ({ page }) => {
  let status = 'pending'
  const event = () => ({
    id: 91, event_no: 'P2B-EVENT-MOCK-01', request_key: 'P2B-REQUEST-MOCK-01', kind: 'fx_settlement', currency: 'USD', amount: '100.0000', direction: 'income', bank_date: '2026-10-19', bank_net_amount: '705.00', fee_mode: 'none', fee_amount: '0.00', source_account: 'SYNTH-FX-01', rmb_account: 'SYNTH-CNY-01', bank_reference: 'P2B-MOCK-BANK-01', evidence_reference: 'P2B-MOCK-VOUCHER-01', evidence_sha256: 'a'.repeat(64), evidence_note: 'mock voucher checked', private_voucher: 1, status, confirmed_at: status === 'confirmed' ? '2026-10-19T02:00:00Z' : null, sources: [{ transaction_id: 1, amount: '30.0000', currency: 'USD', snapshot: { transaction_no: 'P2B-SYNTH-T', exchange_rate: '7.100000' } }, { transaction_id: 2, amount: '70.0000', currency: 'USD', snapshot: { transaction_no: 'P2B-SYNTH-T-SPLIT', exchange_rate: '7.100000' } }], reference_amount: '710.00', net_minus_reference_information_only: '-5.00', note: '仅人工凭证确认事实；含扣费不再次扣减净额。', quoted_rate: '7.100000', fee_for: null,
  })
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
    if (path === '/api/rmb-cash-events/' && route.request().method() === 'GET') return route.fulfill({ json: { results: status === 'pending' ? [] : [event()] } })
    if (path === '/api/rmb-cash-events/accounts/') return route.fulfill({ json: { results: [
      { code: 'SYNTH-FX-01', name: '合成外币账户', currency: 'USD' },
      { code: 'SYNTH-CNY-01', name: '合成人民币账户', currency: 'CNY' },
    ] } })
    if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [{ id: 1, transaction_no: 'P2B-SYNTH-T', currency: 'USD', direction: 'income', amount: '30.0000', remaining_candidate_amount: '30.0000', blocked_reason: null }, { id: 2, transaction_no: 'P2B-SYNTH-T-SPLIT', currency: 'USD', direction: 'income', amount: '70.0000', remaining_candidate_amount: '70.0000', blocked_reason: null }] } })
    if (path === '/api/rmb-cash-events/preview/') return route.fulfill({ json: { source_total: '100.00', bank_net_amount: '705.00', confirmed: false, sources: [] } })
    if (path === '/api/rmb-cash-events/voucher-upload/') return route.fulfill({ status: 201, json: { id: 1, name: 'synthetic-bank.pdf', sha256: 'a'.repeat(64) } })
    if (path === '/api/rmb-cash-events/91/duplicate-candidates/') return route.fulfill({ json: { count: 0, items: [], restricted: false, token: 'empty' } })
    if (path === '/api/rmb-cash-events/' && route.request().method() === 'POST') return route.fulfill({ status: 201, json: event() })
    if (path === '/api/rmb-cash-events/91/confirm/') { status = 'confirmed'; return route.fulfill({ json: event() }) }
    return route.fulfill({ json: [] })
  })
  await page.goto('/rmb-cash-events', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('.cash-page-head').getByRole('heading', { name: '银行资金记录', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '新增资金事件' }).click()
  await page.getByLabel('扣费前兑换额（CNY）').fill('705.00')
  await page.getByLabel('参考折算汇率').fill('7.100000')
  await page.getByRole('combobox', { name: '来源账户', exact: true }).selectOption('SYNTH-FX-01')
  await page.getByRole('combobox', { name: '人民币账户', exact: true }).selectOption('SYNTH-CNY-01')
  await page.getByLabel('银行参考号').fill('P2B-MOCK-BANK-01')
  await page.getByLabel('核对说明').fill('mock voucher checked')
  await page.getByRole('button', { name: '选择', exact: true }).nth(0).click()
  await page.getByRole('button', { name: '选择', exact: true }).last().click()
  await page.locator('.allocation-table input[type="number"]').nth(0).fill('30.00')
  await page.locator('.allocation-table input[type="number"]').nth(1).fill('70.00')
  await page.locator('.verification-toggle input').nth(0).check()
  await page.locator('.verification-toggle input').nth(1).check()
  await page.getByLabel('银行凭证文件', { exact: true }).setInputFiles({
    name: 'synthetic-bank.pdf', mimeType: 'application/pdf', buffer: syntheticVoucherPdf(),
  })
  await page.getByRole('button', { name: '上传并校验凭证', exact: true }).click()
  await expect(page.getByText('凭证已上传：synthetic-bank.pdf。确认时将再次校验。')).toBeVisible()
  await page.getByRole('button', { name: '预览结汇信息' }).click()
  await expect(page.locator('.preview-box')).toContainText('来源合计 USD 100.00')
  await page.getByRole('button', { name: '登记待确认结汇' }).click()
  await expect(page.locator('.review-banner')).toContainText('待确认')
  await expect(page.getByRole('button', { name: '确认银行凭证' })).toBeDisabled()
  await page.getByRole('checkbox', { name: /我已核对银行凭证/ }).check()
  await page.getByRole('button', { name: '确认银行凭证' }).click()
  await expect(page.locator('.review-banner')).toContainText('已确认')
})

test('source verification is explicit and any fact change invalidates the preview', async ({ page }) => {
  let previewCalls = 0
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
    if (path === '/api/rmb-cash-events/accounts/') return route.fulfill({ json: { results: [
      { code: 'SYNTH-FX-01', name: '合成外币账户', currency: 'USD' },
      { code: 'SYNTH-CNY-01', name: '合成人民币账户', currency: 'CNY' },
    ] } })
    if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [{ id: 1, transaction_no: 'P2B-SOURCE-1', currency: 'USD', direction: 'income', amount: '100.00', remaining_candidate_amount: '100.00', blocked_reason: null }] } })
    if (path === '/api/rmb-cash-events/preview/') { previewCalls += 1; return route.fulfill({ json: { source_total: '100.00', bank_net_amount: '705.00', confirmed: false, sources: [] } }) }
    return route.fulfill({ json: [] })
  })
  await page.goto('/rmb-cash-events', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '新增资金事件' }).click()
  await page.getByLabel('扣费前兑换额（CNY）').fill('705.00')
  await page.getByRole('combobox', { name: '来源账户', exact: true }).selectOption('SYNTH-FX-01')
  await page.getByRole('combobox', { name: '人民币账户', exact: true }).selectOption('SYNTH-CNY-01')
  await page.getByLabel('银行参考号').fill('P2B-PREVIEW-INVALIDATE')
  await page.getByRole('button', { name: '选择', exact: true }).click()
  await page.locator('.allocation-table input[type="number"]').fill('100.00')
  await page.getByRole('button', { name: '预览结汇信息' }).click()
  await expect(page.getByRole('alert')).toContainText('逐条核实')
  await page.locator('.verification-toggle input').check()
  await page.getByRole('button', { name: '预览结汇信息' }).click()
  await expect(page.locator('.preview-box')).toBeVisible()
  expect(previewCalls).toBe(1)
  await page.getByLabel('扣费前兑换额（CNY）').fill('706.00')
  await expect(page.locator('.preview-box')).toHaveCount(0)
  await expect(page.getByText('表单已修改，请重新预览。')).toBeVisible()
  await expect(page.getByRole('button', { name: '预览结汇信息' })).toBeVisible()
})

test('refresh retains the stable request identity without persisting financial inputs', async ({ page }) => {
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
    if (path === '/api/rmb-cash-events/accounts/') return route.fulfill({ json: { results: [
      { code: 'SYNTH-FX-01', name: '合成外币账户', currency: 'USD' },
      { code: 'SYNTH-CNY-01', name: '合成人民币账户', currency: 'CNY' },
    ] } })
    if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [] } })
    return route.fulfill({ json: [] })
  })
  await page.goto('/rmb-cash-events', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '新增资金事件' }).click()
  const requestKey = await page.getByLabel('稳定请求键').inputValue()
  await page.getByLabel('扣费前兑换额（CNY）').fill('705.00')
  await page.reload()
  await page.getByRole('button', { name: '新增资金事件' }).click()
  await expect(page.getByLabel('稳定请求键')).toHaveValue(requestKey)
  await expect(page.getByLabel('扣费前兑换额（CNY）')).toHaveValue('')
  const stored = await page.evaluate(() => Object.values(sessionStorage).join('\n'))
  expect(stored).toContain(requestKey)
  expect(stored).not.toContain('bank_net_amount')
  expect(await page.evaluate(() => localStorage.getItem('sunjack:r1-fin-p2-b:cash-event-draft:v1'))).toBeNull()
})

test('in-memory draft survives task switches and explicit abandon clears only after confirmation', async ({ page }) => {
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
    if (path === '/api/rmb-cash-events/accounts/') return route.fulfill({ json: { results: [
      { code: 'SYNTH-FX-01', name: '合成外币账户', currency: 'USD' },
      { code: 'SYNTH-CNY-01', name: '合成人民币账户', currency: 'CNY' },
    ] } })
    if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [] } })
    return route.fulfill({ json: [] })
  })
  await page.goto('/rmb-cash-events', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '新增资金事件' }).click()
  await page.getByLabel('扣费前兑换额（CNY）').fill('705.00')
  await page.getByRole('link', { name: '客户管理', exact: true }).click()
  await page.getByRole('tab', { name: /^银行资金记录/ }).click()
  await expect(page.getByLabel('扣费前兑换额（CNY）')).toHaveValue('705')
  await page.getByRole('button', { name: '取消', exact: true }).click()
  await expect(page.getByRole('heading', { name: '未保存修改', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '继续编辑', exact: true }).click()
  await expect(page.getByLabel('扣费前兑换额（CNY）')).toHaveValue('705')
  await page.getByRole('button', { name: '取消', exact: true }).click()
  await page.getByRole('button', { name: '放弃修改', exact: true }).click()
  await expect(page.getByRole('heading', { name: '新增资金事件', exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: '新增资金事件' }).click()
  await expect(page.getByLabel('扣费前兑换额（CNY）')).toHaveValue('')
})

test('changing a 30 allocation to 50 clears verification and requires a fresh preview', async ({ page }) => {
  let previewCalls = 0
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
    if (path === '/api/rmb-cash-events/accounts/') return route.fulfill({ json: { results: [
      { code: 'SYNTH-FX-01', name: '合成外币账户', currency: 'USD' },
      { code: 'SYNTH-CNY-01', name: '合成人民币账户', currency: 'CNY' },
    ] } })
    if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [{ id: 1, transaction_no: 'P2B-30-50-SOURCE', currency: 'USD', direction: 'income', amount: '100.00', remaining_candidate_amount: '100.00', blocked_reason: null }] } })
    if (path === '/api/rmb-cash-events/preview/') { previewCalls += 1; return route.fulfill({ json: { source_total: '30.00', bank_net_amount: '213.00', confirmed: false, sources: [] } }) }
    return route.fulfill({ json: [] })
  })
  await page.goto('/rmb-cash-events', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '新增资金事件' }).click()
  await page.getByLabel('扣费前兑换额（CNY）').fill('213.00')
  await page.getByRole('combobox', { name: '来源账户', exact: true }).selectOption('SYNTH-FX-01')
  await page.getByRole('combobox', { name: '人民币账户', exact: true }).selectOption('SYNTH-CNY-01')
  await page.getByLabel('银行参考号').fill('P2B-30-50')
  await page.getByRole('button', { name: '选择', exact: true }).click()
  await page.locator('.allocation-table input[type="number"]').fill('30')
  await page.locator('.verification-toggle input').check()
  await page.getByRole('button', { name: '预览结汇信息' }).click()
  await expect(page.locator('.preview-box')).toBeVisible()
  expect(previewCalls).toBe(1)
  await page.locator('.allocation-table input[type="number"]').fill('50')
  await expect(page.locator('.verification-toggle input')).not.toBeChecked()
  await expect(page.locator('.preview-box')).toHaveCount(0)
  await expect(page.getByText('表单已修改，请重新预览。')).toBeVisible()
  await page.getByRole('button', { name: '预览结汇信息' }).click()
  await expect(page.getByRole('alert')).toHaveText('请逐条核实本次使用的来源流水后再预览。')
  expect(previewCalls).toBe(1)
  await page.locator('.verification-toggle input').check()
  await page.getByRole('button', { name: '预览结汇信息' }).click()
  await expect(page.locator('.preview-box')).toBeVisible()
  expect(previewCalls).toBe(2)
})

test('expired local draft is removed during page initialization and sensitive evidence is not persisted', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('sunjack:r1-fin-p2-b:cash-event-draft:v1', JSON.stringify({
      saved_at: Date.now() - 25 * 60 * 60 * 1000,
      form: { request_key: 'EXPIRED-REQUEST', evidence_sha256: 'secret-hash', evidence_note: 'private note' },
      allocations: [],
    }))
  })
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
    if (path === '/api/rmb-cash-events/accounts/') return route.fulfill({ json: { results: [
      { code: 'SYNTH-FX-01', name: '合成外币账户', currency: 'USD' },
      { code: 'SYNTH-CNY-01', name: '合成人民币账户', currency: 'CNY' },
    ] } })
    if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [] } })
    return route.fulfill({ json: [] })
  })
  await page.goto('/rmb-cash-events', { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('button', { name: '新增资金事件', exact: true })).toBeVisible()
  expect(await page.evaluate(() => localStorage.getItem('sunjack:r1-fin-p2-b:cash-event-draft:v1'))).toBeNull()
  await page.getByRole('button', { name: '新增资金事件' }).click()
  await page.getByLabel('扣费前兑换额（CNY）').fill('705.00')
  await page.getByLabel('核对说明').fill('private-browser-evidence-never-persist')
  const raw = await page.evaluate(() => Object.entries(sessionStorage).find(([key]) => key.startsWith('sunjack:cash-event:request-identity:v1:'))?.[1])
  const identity = JSON.parse(raw)
  expect(Object.keys(identity).sort()).toEqual(['attempted', 'event_no', 'request_key', 'saved_at'])
  expect(identity).not.toHaveProperty('form')
  expect(identity).not.toHaveProperty('allocations')
  expect(raw).not.toContain('bank_net_amount')
  expect(raw).not.toContain('private-browser-evidence-never-persist')
  expect(await page.evaluate(() => localStorage.getItem('sunjack:r1-fin-p2-b:cash-event-draft:v1'))).toBeNull()
})

test('legacy unscoped financial inputs are removed and never restored into a workspace', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('sunjack:r1-fin-p2-b:cash-event-draft:v1', JSON.stringify({
      version: 1,
      saved_at: Date.now(),
      form: {
        request_key: 'LEGACY-REQUEST', event_no: 'LEGACY-EVENT', bank_net_amount: '705.00',
        evidence_reference: 'legacy-secret-voucher', evidence_sha256: 'b'.repeat(64), evidence_note: 'legacy private note',
      },
      allocations: [],
    }))
  })
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
    if (path === '/api/rmb-cash-events/accounts/') return route.fulfill({ json: { results: [
      { code: 'SYNTH-FX-01', name: '合成外币账户', currency: 'USD' },
      { code: 'SYNTH-CNY-01', name: '合成人民币账户', currency: 'CNY' },
    ] } })
    if (path === '/api/rmb-cash-events/sources/') return route.fulfill({ json: { results: [] } })
    return route.fulfill({ json: [] })
  })
  await page.goto('/rmb-cash-events', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '新增资金事件' }).click()
  await expect(page.getByText('旧版浏览器草稿已清理', { exact: false })).toBeVisible()
  expect(await page.evaluate(() => localStorage.getItem('sunjack:r1-fin-p2-b:cash-event-draft:v1'))).toBeNull()
  await expect(page.getByLabel('稳定请求键')).not.toHaveValue('LEGACY-REQUEST')
  await expect(page.getByLabel('扣费前兑换额（CNY）')).toHaveValue('')
  await expect(page.getByLabel('凭证引用')).toHaveValue('')
  const stored = await page.evaluate(() => [...Object.values(localStorage), ...Object.values(sessionStorage)].join('\n'))
  expect(stored).not.toContain('legacy-secret-voucher')
  expect(stored).not.toContain('legacy private note')
})

test('stale source responses cannot overwrite the current currency', async ({ page }) => {
  await page.route('**/api/**', async route => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { development_superadmin: true, has_all_permissions: true } })
    if (path === '/api/rmb-cash-events/accounts/') return route.fulfill({ json: { results: [
      { code: 'SYNTH-FX-01', name: '合成外币账户', currency: 'USD' },
      { code: 'SYNTH-CNY-01', name: '合成人民币账户', currency: 'CNY' },
    ] } })
    if (path === '/api/rmb-cash-events/sources/') {
      const currency = new URL(request.url()).searchParams.get('currency')
      if (currency === 'USD') {
        await new Promise(resolve => setTimeout(resolve, 250))
        return route.fulfill({ json: { results: [{ id: 1, transaction_no: 'STALE-USD', currency: 'USD', direction: 'income', amount: '100.00', remaining_candidate_amount: '100.00', blocked_reason: null }] } })
      }
      return route.fulfill({ json: { results: [{ id: 2, transaction_no: 'CURRENT-CNY', currency: 'CNY', direction: 'income', amount: '100.00', remaining_candidate_amount: '100.00', blocked_reason: null }] } })
    }
    return route.fulfill({ json: [] })
  })
  await page.goto('/rmb-cash-events', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '新增资金事件' }).click()
  await page.getByLabel('事件类型').selectOption('cny_direct')
  await expect(page.locator('.source-option')).toContainText('CURRENT-CNY')
  await page.waitForTimeout(350)
  await expect(page.locator('.source-option')).not.toContainText('STALE-USD')
})
