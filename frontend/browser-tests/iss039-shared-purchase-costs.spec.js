import { test, expect } from '@playwright/test'
import path from 'node:path'

const evidenceDir = path.resolve(process.cwd(), '../docs/uat-evidence/iss-039-integration')

const purchase = {
  id: 1,
  purchase_no: 'ISS039-PO-001',
  supplier_name: 'ISS039 供应商',
  order_date: '2026-10-24',
  expected_arrival_date: '2026-11-01',
  status: 'ordered',
  status_display: '已下单',
  currency: 'CNY',
  total_amount: '10000',
  paid_amount: '0',
  unpaid_amount: '10000',
  items: [{
    id: 11,
    sku: 501,
    sku_code: 'ISS039-SKU-01',
    display_name: 'ISS039 线性灯',
    quantity: '10',
    unit_price: '1000',
    amount: '10000',
    received_quantity: '0',
    remaining_quantity: '10',
    trade_quantity: '10',
    trade_unit: '件',
    trade_snapshot: { base_unit: '件', unit: '件', factor: 1 },
  }],
  related_orders: [{ id: 101, order_no: 'ISS039-SO-A' }, { id: 102, order_no: 'ISS039-SO-B' }],
}

const allocation = {
  version: 2,
  can_edit: true,
  read_only_reason: '',
  allocations: [
    { purchase_item: 11, target_type: 'order', order: 101, order_no: 'ISS039-SO-A', sales_link_restricted: true, quantity: '3', base_amount: '3000', additional_amount: '300', total_amount: '3300' },
    { purchase_item: 11, target_type: 'order', order: 102, order_no: 'ISS039-SO-B', sales_link_restricted: true, quantity: '2', base_amount: '2000', additional_amount: '200', total_amount: '2200' },
    { purchase_item: 11, target_type: 'inventory', order: null, quantity: '5', base_amount: '5000', additional_amount: '500', total_amount: '5500' },
  ],
  expenses: [{ name: '公共运费', amount: '1000', method: 'amount' }],
  base_amount: '10000',
  additional_amount: '1000',
  total_amount: '11000',
}

const operators = {
  authorized: {
    authenticated: true, rbac_enforcement: true, development_superadmin: false, has_all_permissions: false,
    name: 'ISS039 授权采购员',
    permissions: { purchases: { view: true, update: true }, suppliers: { view: true }, skus: { view: true } },
  },
  readonly: {
    authenticated: true, rbac_enforcement: true, development_superadmin: false, has_all_permissions: false,
    name: 'ISS039 只读采购员',
    permissions: { purchases: { view: true }, suppliers: { view: true }, skus: { view: true } },
  },
  none: {
    authenticated: true, rbac_enforcement: true, development_superadmin: false, has_all_permissions: false,
    name: 'ISS039 无权账号', permissions: {},
  },
}

async function mockPurchaseApi(page, role) {
  const requests = []
  await page.route('**/api/**', async route => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    requests.push({ path, method: request.method() })

    if (path.includes('/session/current-operator/')) return route.fulfill({ json: operators[role] })
    if (path === '/api/purchase-orders/' || path === '/api/purchase-orders/1/') return route.fulfill({ json: [purchase] })
    if (path === '/api/suppliers/' || path === '/api/skus/' || path === '/api/orders/') return route.fulfill({ json: [] })
    if (path === '/api/purchase-orders/cost-allocation-orders/') {
      if (role !== 'authorized') return route.fulfill({ status: 403, json: { detail: '需要采购修改权限才能选择成本归属订单。' } })
      return route.fulfill({ json: [
        { id: 101, order_no: 'ISS039-SO-A', status: 'confirmed', status_display: '已确认' },
        { id: 102, order_no: 'ISS039-SO-B', status: 'confirmed', status_display: '已确认' },
      ] })
    }
    if (path === '/api/purchase-orders/1/cost-allocation/' || path === '/api/purchase-orders/1/cost-allocation-preview/') {
      return route.fulfill({ json: { ...allocation, can_edit: role === 'authorized', read_only_reason: role === 'authorized' ? '' : '需要采购修改权限才能调整成本归属。' } })
    }
    if (path === '/api/purchase-orders/1/' && request.method() === 'POST') return route.fulfill({ json: allocation })
    return route.fulfill({ json: [] })
  })
  return requests
}

test('ISS-039 authorized procurement can restore and edit a cross-order allocation without sales data', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  const requests = await mockPurchaseApi(page, 'authorized')
  await page.goto('/purchase-orders?detail=1')
  await expect(page.getByRole('heading', { name: /ISS039-PO-001/ })).toBeVisible()
  await expect(page.getByRole('button', { name: '分配采购成本 / 公共费用' })).toBeVisible()
  await page.getByRole('button', { name: '分配采购成本 / 公共费用' }).click()
  const modal = page.locator('.cost-modal')
  await expect(modal).toContainText('ISS039-SO-A')
  await expect(modal).toContainText('ISS039-SO-B')
  await expect(modal).toContainText('300.00')
  await expect(modal).toContainText('200.00')
  await expect(modal).toContainText('500.00')
  await expect(modal).not.toContainText('客户A')
  await expect(modal).not.toContainText('销售价格')
  await expect(modal.locator('select').nth(1)).toContainText('ISS039-SO-A')
  await expect(modal.locator('select').nth(1)).toContainText('ISS039-SO-B')
  expect(requests.some(request => request.path === '/api/orders/')).toBe(false)
  expect(requests.some(request => request.path === '/api/purchase-orders/cost-allocation-orders/')).toBe(true)
  await page.screenshot({ path: path.join(evidenceDir, 'authorized-1440px.png'), fullPage: true })

  await page.getByRole('button', { name: '保存成本分配' }).click()
  await expect(modal).toContainText('已保存的成本分摊结果')
  await page.reload()
  await expect(page.getByRole('heading', { name: /ISS039-PO-001/ })).toBeVisible()
  await page.screenshot({ path: path.join(evidenceDir, 'authorized-refresh-1440px.png'), fullPage: true })

  await page.setViewportSize({ width: 700, height: 1000 })
  await page.getByRole('button', { name: '分配采购成本 / 公共费用' }).click()
  await expect(page.locator('.cost-modal')).toContainText('ISS039-SO-A')
  await page.screenshot({ path: path.join(evidenceDir, 'authorized-700px.png'), fullPage: true })
})

test('ISS-039 read-only procurement is refused by the candidate API and has no edit action', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  const requests = await mockPurchaseApi(page, 'readonly')
  await page.goto('/purchase-orders?detail=1')
  await expect(page.getByRole('heading', { name: /ISS039-PO-001/ })).toBeVisible()
  await expect(page.getByRole('button', { name: '分配采购成本 / 公共费用' })).toHaveCount(0)
  const refusal = await page.evaluate(async () => {
    const response = await fetch('/api/purchase-orders/cost-allocation-orders/')
    return { status: response.status, body: await response.json() }
  })
  expect(refusal).toEqual({ status: 403, body: { detail: '需要采购修改权限才能选择成本归属订单。' } })
  expect(requests.some(request => request.path === '/api/orders/')).toBe(false)
  await page.screenshot({ path: path.join(evidenceDir, 'readonly-1440px.png'), fullPage: true })
})

test('ISS-039 no-permission role cannot restore the purchase URL', async ({ page }) => {
  await page.setViewportSize({ width: 700, height: 1000 })
  await mockPurchaseApi(page, 'none')
  await page.goto('/purchase-orders?detail=1')
  await expect(page).toHaveURL(/\/access-denied\?from=\/purchase-orders\?detail=1/)
  await expect(page.getByRole('heading', { name: '没有此页面的访问权限' })).toBeVisible()
  await page.screenshot({ path: path.join(evidenceDir, 'no-permission-700px.png'), fullPage: true })
})
