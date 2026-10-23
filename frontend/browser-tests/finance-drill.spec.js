import { test, expect } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const evidenceDir = fileURLToPath(new URL('../../docs/uat-evidence/iss-048-finance-drill/', import.meta.url))

const dashboard = {
  period: { date_from: '2026-10-01', date_to: '2026-10-23' },
  metrics: {
    sales_rmb: '1234.50', estimated_profit_rmb: '234.50', purchase_cost_rmb: '800.00', order_expense_rmb: '200.00',
    income_rmb: '500.00', expense_rmb: '100.00', net_cash_rmb: '400.00', receivable_count: 1, receivable_rmb: '700.00',
    payable_count: 1, payable_rmb: '300.00', advance_receipt_rmb: '50.00', advance_payment_rmb: '20.00',
  },
  due_items: [], categories: [], monthly_cash: [], cash_basis: { note: '账面人民币折算参考，不代表银行实际到账。' },
}

const actual = {
  basis: 'bank_cash_confirmed_v1', period: dashboard.period,
  note: '已登记银行资金汇总。', totals: { inflow: '600.00', outflow: '0.00', net: '600.00', count: 1 }, monthly: [], by_kind: [],
  events: [{ id: 1, bank_date: '2026-10-10', event_no: 'BANK-001', kind_label: '人民币直接收付', direction_label: '流入', bank_net_amount: '600.00', bank_reference: 'REF-001', detail_url: '/rmb-cash-events?event=1' }],
}

const detail = {
  metric: 'sales_rmb', title: '合同销售额', basis_note: '订单日期范围内的正式销售订单；合同变更不分配至商品行。',
  date_basis: 'order_date', amount_unit: '人民币', current_balance: false, period: dashboard.period,
  total_count: 1, total_amount: '1234.50', page: 1, page_size: 50, has_more: false,
  rows: [{ id: 7, record_label: 'SO-ISS-048-001', date: '2026-10-09', relation_label: '明细客户', status_label: '已确认', amount: '1234.50', amount_note: '含已批准合同变更后的合同金额。', detail_url: '/orders?detail=7', detail_label: '查看订单' }],
}

async function mockApi(page) {
  await page.route('**/api/**', async route => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname === '/api/session/current-operator/') return route.fulfill({ json: { authenticated: true, development_superadmin: true, has_all_permissions: true } })
    if (url.pathname === '/api/finance-dashboard/') return route.fulfill({ json: dashboard })
    if (url.pathname === '/api/actual-rmb-cash/') return route.fulfill({ json: actual })
    if (url.pathname === '/api/finance-dashboard/details/') return route.fulfill({ json: detail })
    return route.fulfill({ json: [] })
  })
}

for (const width of [1440, 700]) {
  test(`finance dashboard composition drill desktop and narrow ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 })
    await mockApi(page)
    await page.goto('/finance?date_from=2026-10-01&date_to=2026-10-23')
    await expect(page.getByText('合同销售额', { exact: true }).first()).toBeVisible()
    await page.getByRole('button', { name: '查看构成明细', exact: true }).first().click()
    await expect(page.locator('.finance-drill-panel')).toContainText('SO-ISS-048-001')
    await expect(page.locator('.finance-drill-panel')).toContainText('¥1,234.50')
    await expect(page.locator('.finance-drill-panel a[href="/orders?detail=7"]')).toBeVisible()
    await page.waitForTimeout(width === 700 ? 500 : 100)
    await page.screenshot({ path: `${evidenceDir}finance-drill-${width}.png`, fullPage: true })
    await page.getByRole('button', { name: '收起明细', exact: true }).click()
    await expect(page.locator('.finance-drill-panel')).toHaveCount(0)
    await page.getByRole('button', { name: '查看构成明细', exact: true }).last().click()
    await expect(page.locator('.actual-cash-events')).toBeInViewport()
    await page.waitForTimeout(width === 700 ? 500 : 100)
    await page.screenshot({ path: `${evidenceDir}finance-bank-events-${width}.png`, fullPage: true })
  })
}
