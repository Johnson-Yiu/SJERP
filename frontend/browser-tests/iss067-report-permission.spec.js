import { test, expect } from '@playwright/test'
import { mockApi } from './reporting-fixtures.js'

const oldSalesUrl = '/reports?source=sales&group_by=customer&grain=month&date_field=order_date&metric=amount&view=bar&comparison=previous&date_from=2026-09-01&date_to=2026-10-23&filter_country=China'

test('employee opening an old unauthorized report URL gets a valid source and keeps the warning', async ({ page }) => {
  const state = await mockApi(page, { restricted: true })
  await page.goto(oldSalesUrl)

  const source = page.getByRole('combobox', { name: '数据来源', exact: true })
  await expect(source).toHaveValue('customers')
  await expect(source.locator('option')).toHaveCount(1)
  await expect(page.getByRole('alert')).toContainText('地址中的报表来源当前不可查看')
  await expect(page.locator('.report-block')).toHaveCount(0)
  expect(state.reportRequests).toHaveLength(0)
  await page.screenshot({ path: 'docs/uat-evidence/iss-067-report-permission/employee-old-url-1440.png', fullPage: true })

  await page.getByRole('link', { name: '经营概览', exact: true }).click()
  await page.goBack()
  await expect(page).toHaveURL(/source=sales/)
  await expect(page.getByRole('combobox', { name: '数据来源', exact: true })).toHaveValue('customers')
  await expect(page.getByRole('alert')).toContainText('地址中的报表来源当前不可查看')

  await page.getByRole('button', { name: '查询报表', exact: true }).click()
  await expect(page).toHaveURL(/source=customers/)
  await expect(page).not.toHaveURL(/source=sales/)
  await expect(page.locator('.reports-page > .report-block .block-kpis')).toBeVisible()
  expect(state.reportRequests.at(-1).get('source')).toBe('customers')

  await page.getByRole('button', { name: '保存为图表块', exact: true }).click()
  await expect(page.locator('.saved-block')).toHaveCount(1)
  await page.reload()
  await expect(source).toHaveValue('customers')
  await expect(page.locator('.reports-page > .report-block .block-kpis')).toBeVisible()
  await expect(page.locator('.saved-block')).toHaveCount(1)
  await page.screenshot({ path: 'docs/uat-evidence/iss-067-report-permission/employee-authorized-source-1440.png', fullPage: true })

  await page.setViewportSize({ width: 700, height: 1000 })
  await page.goto(oldSalesUrl)
  await expect(page.getByRole('combobox', { name: '数据来源', exact: true })).toHaveValue('customers')
  await expect(page.getByRole('alert')).toContainText('地址中的报表来源当前不可查看')
  await page.screenshot({ path: 'docs/uat-evidence/iss-067-report-permission/employee-old-url-700.png', fullPage: true })
})

test('shared template path remains available to an employee with the source permission', async ({ page }) => {
  const state = { templates: [{ id: 1, name: '团队销售模板', description: '', config: { source: 'sales', group_by: 'country', group_by_2: '', date_field: 'order_date', grain: 'month', metric: 'amount', view: 'bar', comparison: 'previous', title: '团队销售模板', filters: {} }, published: true, published_at: '2026-10-23T09:00:00Z', config_version: 2, can_use: true, can_manage: false }], nextId: 2 }
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    if (url.pathname.includes('current-operator')) return route.fulfill({ json: { authenticated: true, development_superadmin: false, has_all_permissions: false, rbac_enforcement: true, permissions: { reports: { view: true }, orders: { view: true }, customers: { view: true }, products: { view: true }, skus: { view: true }, categories: { view: true } } } })
    if (url.pathname === '/api/reports/catalog/') return route.fulfill({ json: { sources: { sales: { label: '销售报表', dimensions: ['time', 'customer', 'country'], dates: { order_date: '订单日期' }, note: '有效销售合同金额。' } }, dimensions: { time: '时间', customer: '客户', country: '国家/地区' }, grains: { month: '月' } } })
    if (url.pathname === '/api/reports/templates/' && route.request().method() === 'GET') return route.fulfill({ json: { count: state.templates.length, next: null, previous: null, results: state.templates } })
    if (url.pathname === '/api/reports/data/') return route.fulfill({ json: { source: 'sales', group_by: 'country', date_field: 'order_date', period: { date_from: '2026-01-01', date_to: '2026-10-23' }, comparison_period: { date_from: '2025-01-01', date_to: '2025-10-23' }, comparison: 'previous', totals: { amount: '100', count: 1, quantities: {} }, changes: { amount: 0, count: 0 }, rows: [{ key: 'CN', label: '中国', amount: '100', count: 1, quantities: {} }], filters: {}, filter_summary: [], note: '共享模板测试数据。' } })
    return route.fulfill({ json: [] })
  })
  await page.goto('/reports?shared_template=1&source=sales&group_by=country&date_field=order_date&grain=month&metric=amount&view=bar&comparison=previous&date_from=2026-01-01&date_to=2026-10-23')
  await expect(page.locator('.active-template-note')).toContainText('团队销售模板')
  await expect(page.locator('.reports-page > .report-block .block-kpis')).toBeVisible()
})
