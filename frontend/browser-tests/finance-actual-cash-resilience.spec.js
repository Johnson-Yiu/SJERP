import { test, expect } from '@playwright/test'

const dashboard = (from = '2026-10-01', to = '2026-10-19') => ({
  period: { date_from: from, date_to: to },
  metrics: {
    sales_rmb: '500.00', estimated_profit_rmb: '100.00', purchase_cost_rmb: '300.00', order_expense_rmb: '0.00',
    income_rmb: '340.00', expense_rmb: '0.00', net_cash_rmb: '340.00', receivable_count: 1, receivable_rmb: '160.00',
    payable_count: 0, payable_rmb: '0.00', advance_receipt_rmb: '0.00', advance_payment_rmb: '0.00',
  }, due_items: [], cash_basis: { note: '账面人民币折算参考，不代表银行实际到账。' }, monthly_cash: [], categories: [],
})

const actual = (amount, from, to) => ({
  basis: 'bank_cash_confirmed_v1', period: { date_from: from, date_to: to },
  note: '已登记银行资金汇总。', totals: { inflow: amount, outflow: '0.00', net: amount, count: 1 }, monthly: [], by_kind: [],
  events: [{ id: amount, bank_date: from, event_no: `FIX-${amount}`, kind_label: '人民币直接收付', direction_label: '流入', bank_net_amount: amount, bank_reference: 'BANK-REF' }],
})

async function mockCommon(page, actualHandler) {
  await page.route('**/api/**', async route => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { authenticated: true, development_superadmin: true, has_all_permissions: true } })
    if (path === '/api/finance-dashboard/') {
      return route.fulfill({ json: dashboard(url.searchParams.get('date_from') || undefined, url.searchParams.get('date_to') || undefined) })
    }
    if (path === '/api/actual-rmb-cash/') return actualHandler(route, url)
    return route.fulfill({ json: [] })
  })
}

test('actual cash failure leaves the legacy dashboard available and retry is independent', async ({ page }) => {
  let actualCalls = 0
  await mockCommon(page, async route => {
    actualCalls += 1
    if (actualCalls === 1) return route.fulfill({ status: 400, json: { detail: 'temporary failure' } })
    return route.fulfill({ json: actual('705.00', '2026-10-01', '2026-10-19') })
  })
  await page.goto('/finance?date_from=2026-10-01&date_to=2026-10-19')
  await expect(page.getByText('合同销售额', { exact: true })).toBeVisible()
  await expect(page.getByText('temporary failure')).toBeVisible()
  await expect(page.getByText('¥340.00', { exact: true }).first()).toBeVisible()
  await page.getByRole('button', { name: '重新加载', exact: true }).click()
  await page.waitForTimeout(250)
  await expect(page.getByRole('heading', { name: '银行实际人民币资金', exact: true })).toBeVisible()
  await expect(page.getByText('¥705.00', { exact: true }).first()).toBeVisible()
  expect(actualCalls).toBe(2)
})

test('rapid date changes discard stale actual cash responses', async ({ page }) => {
  let actualCalls = 0
  await mockCommon(page, async (route, url) => {
    actualCalls += 1
    const from = url.searchParams.get('date_from')
    if (from === '2026-10-01') {
      await new Promise(resolve => setTimeout(resolve, 300))
      return route.fulfill({ json: actual('100.00', from, '2026-10-19') })
    }
    return route.fulfill({ json: actual('200.00', from, '2026-09-30') })
  })
  await page.goto('/finance?date_from=2026-10-01&date_to=2026-10-19')
  await page.getByLabel('开始日期').fill('2026-09-01')
  await page.getByLabel('结束日期').fill('2026-09-30')
  await page.getByRole('button', { name: '查询', exact: true }).click()
  await expect(page.locator('.actual-cash-cards').getByText('¥200.00', { exact: true }).first()).toBeVisible()
  await page.waitForTimeout(350)
  await expect(page.locator('.actual-cash-section').getByText('¥100.00', { exact: true })).toHaveCount(0)
  await expect(page.locator('.actual-cash-section')).toContainText('2026-09-01')
  expect(actualCalls).toBeGreaterThanOrEqual(2)
})

