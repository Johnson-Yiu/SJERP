import path from 'node:path'
import { expect, test } from '@playwright/test'

const evidenceDir = process.env.R1_REPAIR_EVIDENCE_DIR
  ? path.resolve(process.env.R1_REPAIR_EVIDENCE_DIR)
  : path.resolve(process.cwd(), '..', 'docs', 'uat-evidence', 'r1-hist-01-fix-04')

async function layoutMetrics(page) {
  return page.evaluate(() => ({
    viewport: window.innerWidth,
    pageWidth: document.documentElement.scrollWidth,
    bodyWidth: document.body.scrollWidth,
    tables: [...document.querySelectorAll('.analysis-table-wrap')].map(element => ({
      width: element.clientWidth,
      scrollWidth: element.scrollWidth,
    })),
  }))
}

async function assertSkuQuantitiesAreVisible(page) {
  const result = await page.locator('.analysis-detail-card').evaluateAll(cards => cards
    .filter(card => card.querySelector('h5')?.textContent.trim() === 'SKU')
    .map(card => {
    const wrapper = card.querySelector('.analysis-table-wrap')
    const table = wrapper.querySelector('.analysis-table')
    const wrapperRect = wrapper.getBoundingClientRect()
    const tableRect = table.getBoundingClientRect()
    const quantityCells = [...table.querySelectorAll('tbody td:nth-child(3)')]
      .filter(cell => ['17', '27'].includes(cell.textContent.trim()))
      .map(cell => {
        const rect = cell.getBoundingClientRect()
        return {
          text: cell.textContent.trim(),
          fullyVisible: rect.left >= wrapperRect.left && rect.right <= wrapperRect.right,
        }
      })
    return {
      clientWidth: wrapper.clientWidth,
      scrollWidth: wrapper.scrollWidth,
      tableWidth: tableRect.width,
      quantityCells,
    }
  }))
  const quantityCells = result.flatMap(table => table.quantityCells)
  expect(quantityCells.map(cell => cell.text).sort()).toEqual(['17', '27'])
  expect(quantityCells.every(cell => cell.fullyVisible)).toBe(true)
  expect(result.every(table => table.scrollWidth <= table.clientWidth + 1)).toBe(true)
  expect(result.every(table => table.tableWidth <= table.clientWidth + 1)).toBe(true)
}

test('current historical analysis detail tables match the API at desktop and 700px CSS viewport', async ({ page }) => {
  await page.setViewportSize({ width: 700, height: 900 })
  const apiResponsePromise = page.waitForResponse(response => response.url().includes('/api/reports/historical/') && response.request().method() === 'GET')
  await page.goto('/historical-orders')
  const apiPayload = await (await apiResponsePromise).json()
  const salesSkuQuantities = apiPayload.sales.by_sku.map(row => Number(row.quantity))
  const purchaseSkuQuantities = apiPayload.purchase.by_sku.map(row => Number(row.quantity))
  expect(salesSkuQuantities.reduce((sum, quantity) => sum + quantity, 0)).toBe(Number(apiPayload.sales.quantity))
  expect(purchaseSkuQuantities.reduce((sum, quantity) => sum + quantity, 0)).toBe(Number(apiPayload.purchase.quantity))
  expect(apiPayload.sales.by_sku.find(row => row.label.startsWith('CHROME-SKU'))?.quantity).toBe(17)
  expect(apiPayload.purchase.by_sku.find(row => row.label.startsWith('CHROME-SKU'))?.quantity).toBe(27)
  await expect(page.getByRole('heading', { name: '历史经营分析', exact: true })).toBeVisible()
  await expect(page.locator('.analysis-detail-grid')).toBeVisible()
  await expect(page.locator('.analysis-table')).not.toHaveCount(0)

  const narrowMetrics = await layoutMetrics(page)
  expect(narrowMetrics.viewport).toBe(700)
  expect(narrowMetrics.pageWidth).toBeLessThanOrEqual(700)
  expect(narrowMetrics.bodyWidth).toBeLessThanOrEqual(700)
  expect(narrowMetrics.tables.every(table => table.width <= 700 && table.scrollWidth >= table.width)).toBe(true)
  await assertSkuQuantitiesAreVisible(page)
  await page.screenshot({ path: path.join(evidenceDir, 'playwright-700px.png'), fullPage: true })

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.reload()
  await expect(page.locator('.analysis-detail-grid')).toBeVisible()
  const desktopMetrics = await layoutMetrics(page)
  expect(desktopMetrics.viewport).toBe(1440)
  expect(desktopMetrics.pageWidth).toBeLessThanOrEqual(1440)
  await assertSkuQuantitiesAreVisible(page)
  await page.screenshot({ path: path.join(evidenceDir, 'playwright-desktop.png'), fullPage: true })
})

test('current historical analysis hides unauthorized detail dimensions without blanking the page', async ({ page }) => {
  await page.setViewportSize({ width: 700, height: 900 })
  await page.route('**/api/session/current-operator/', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      name: '销售只读测试员', role: '销售只读', development_superadmin: false,
      has_all_permissions: false, rbac_enforcement: true,
      permissions: { orders: { view: true, create: false }, purchases: { view: false } },
    }),
  }))
  await page.route('**/api/orders/**', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ count: 0, next: null, previous: null, results: [] }),
  }))
  await page.route('**/api/reports/historical/**', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      scope: 'historical_only', label: '历史订单 · 仅用于经营分析',
      sales: { order_count: 0, amount_rmb: '0', quantity: '0', by_customer: [], by_country: [], by_sku: [], by_category: [] },
      purchase: null, profit: { available: false, note: '历史订单未提供可靠成本时，不计算利润。' },
    }),
  }))
  await page.goto('/historical-orders')
  await expect(page.getByRole('heading', { name: '历史经营分析', exact: true })).toBeVisible()
  await expect(page.getByText('当前权限下暂无可展示的历史明细。', { exact: true })).toBeVisible()
  await expect(page.locator('.analysis-detail-grid')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '历史采购订单', exact: true })).toHaveCount(0)
  await expect(page.getByText('客户资料')).toHaveCount(0)
  await page.screenshot({ path: path.join(evidenceDir, 'playwright-700px-permission-limited.png'), fullPage: true })
})
