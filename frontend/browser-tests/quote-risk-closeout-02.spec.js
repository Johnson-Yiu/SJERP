import { expect, test } from '@playwright/test'

const quoteNo = 'CLOSEOUT-Q001'
const sku = { id: 7, sku_code: 'SKU-CLOSEOUT', label: '报价风险合成灯具' }
const quote = {
  id: 1, quote_no: quoteNo, customer: 1, customer_name: '合成客户',
  quote_date: '2026-10-20', valid_until: '2026-11-19', status: 'draft',
  currency: 'USD', exchange_rate: '7.2', total_amount: '200.00',
  items: [{ sku: sku.id, sku_code: sku.sku_code, quantity: '2', unit_price: '100.00' }],
}

async function openQuoteList(page) {
  const state = { risk: 'warning', reports: 0, exports: 0, failExport: false }
  await page.route('**/api/session/current-operator/**', route => route.fulfill({
    json: { name: 'codex', development_superadmin: true, has_all_permissions: true },
  }))
  await page.route('**/api/quotes/**', async route => {
    const { pathname, searchParams } = new URL(route.request().url())
    if (pathname === '/api/quotes/') return route.fulfill({ json: [quote] })
    if (pathname === '/api/quotes/risk-preview/') {
      expect(searchParams.get('sku_ids')).toBe(String(sku.id))
      state.reports++
      if (state.risk === 'unavailable') {
        return route.fulfill({ status: 503, json: { detail: '合成风险服务故障' } })
      }
      return route.fulfill({
        json: { items: state.risk === 'warning' ? [{
          ...sku, sku: sku.id, has_risk: true,
          risk_labels: ['缺少 Sales Model', '缺少有效采购参考成本'],
        }] : [] },
      })
    }
    if (pathname === '/api/quotes/1/export/') {
      state.exports++
      if (state.failExport) return route.fulfill({ status: 503, json: { detail: '合成导出服务故障' } })
      return route.fulfill({
        contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        body: 'synthetic export response',
      })
    }
    return route.continue()
  })
  await page.goto('/quotes')
  const exportButton = page.getByRole('button', { name: '导出 ' + quoteNo, exact: true })
  await expect(exportButton).toBeVisible()
  const notice = page.getByRole('dialog', { name: '导出前风险提示' })
  return { state, exportButton, notice }
}

async function continueDownload(page, notice) {
  const downloaded = page.waitForEvent('download')
  await notice.getByRole('button', { name: '了解风险，继续导出' }).click()
  expect((await downloaded).suggestedFilename()).toBe(quoteNo + '.xlsx')
}

test('报价风险可取消，取消后没有导出请求，再确认才下载', async ({ page }, testInfo) => {
  const { state, exportButton, notice } = await openQuoteList(page)
  await exportButton.click()
  await expect(notice).toContainText('缺少 Sales Model')
  await expect(notice).toContainText('缺少有效采购参考成本')
  await testInfo.attach('quote-risk', { body: await page.screenshot(), contentType: 'image/png' })
  await notice.getByRole('button', { name: '暂不导出' }).click()
  await expect(notice).toHaveCount(0)
  expect(state.exports).toBe(0)

  await exportButton.click()
  await expect(notice).toBeVisible()
  expect(state.reports).toBe(2)
  await continueDownload(page, notice)
  expect(state.exports).toBe(1)
})

test('风险检查服务失败时，需要主动确认后才导出', async ({ page }, testInfo) => {
  const { state, exportButton, notice } = await openQuoteList(page)
  state.risk = 'unavailable'
  await exportButton.click()
  await expect(notice).toContainText('风险检查服务暂时不可用', { timeout: 15000 })
  expect(state.exports).toBe(0)
  await testInfo.attach('quote-risk-unavailable', { body: await page.screenshot(), contentType: 'image/png' })
  await continueDownload(page, notice)
  expect(state.exports).toBe(1)
})

test('导出服务失败后，重试必须重新核对风险', async ({ page }, testInfo) => {
  const { state, exportButton, notice } = await openQuoteList(page)
  state.risk = 'clear'
  state.failExport = true
  await exportButton.click()
  await expect(page.locator('.toast')).toContainText('导出 ' + quoteNo + ' 失败', { timeout: 15000 })
  await testInfo.attach('quote-export-failed', { body: await page.screenshot(), contentType: 'image/png' })
  const failedRequests = state.exports
  expect(failedRequests).toBeGreaterThan(0)
  const previousReports = state.reports

  state.failExport = false
  state.risk = 'warning'
  await exportButton.click()
  await expect(notice).toBeVisible()
  expect(state.reports).toBe(previousReports + 1)
  expect(state.exports).toBe(failedRequests)
  await continueDownload(page, notice)
  expect(state.exports).toBe(failedRequests + 1)
})
