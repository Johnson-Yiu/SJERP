import { test, expect } from '@playwright/test'
import { mockApi } from './reporting-fixtures'

test('submitted labels can precede the data response; capture the actual filtered request', async ({ page }) => {
  const state = await mockApi(page)
  let releaseRequest
  let notifyRequest
  const requestBlocked = new Promise(resolve => { notifyRequest = resolve })
  const release = new Promise(resolve => { releaseRequest = resolve })
  await page.route('**/api/reports/data/**', async route => {
    const url = new URL(route.request().url())
    if (url.searchParams.get('filter_customer') === '1' && !url.searchParams.has('export')) {
      notifyRequest()
      await release
    }
    await route.fallback()
  })
  try {
    await page.goto('/reports')
    await page.getByRole('combobox', { name: '报表预设', exact: true }).selectOption('sales-customer')
    await page.getByRole('combobox', { name: '筛选维度', exact: true }).selectOption('customer')
    await page.getByRole('combobox', { name: '可用值', exact: true }).selectOption('1')
    await page.getByRole('button', { name: '添加筛选', exact: true }).click()
    const responsePromise = page.waitForResponse(response => {
      const url = new URL(response.url())
      return url.pathname === '/api/reports/data/' && url.searchParams.get('filter_customer') === '1'
    })
    await page.getByRole('button', { name: '查询报表', exact: true }).click()
    await requestBlocked
    await expect(page.getByRole('region', { name: '已查询条件' })).toContainText('客户：')
    expect(state.reportRequests.at(-1).get('filter_customer')).toBeNull()
    releaseRequest()
    const response = await responsePromise
    expect(response.status()).toBe(200)
    expect(new URL(response.url()).searchParams.get('filter_customer')).toBe('1')
  } finally {
    releaseRequest()
  }
})
