import { expect, test } from '@playwright/test'

const skus = Array.from({ length: 12 }, (_, index) => {
  const id = index + 1
  return {
    id,
    sku: `INV3-FIX-${String.fromCharCode(64 + id)}`,
    sku_code: `INV3-FIX-${String.fromCharCode(64 + id)}`,
    display_name_cn: `库存差异验收 SKU ${String.fromCharCode(64 + id)}`,
    product_name: `库存差异验收产品 ${id}`,
    sales_model: `INV3-FIX-SM-${String.fromCharCode(64 + id)}`,
    specification: id === 1 ? '24W / 白光' : '',
    description_cn: id === 1 ? '采购参考描述' : '',
    parameter_values: id === 1 ? { 色温: '4000K' } : {},
    product_details: id === 1 ? [{ notes: '可定制线长', custom: '是' }] : [],
    unit: id === 2 ? 'box' : 'pcs',
    default_price: '2',
    currency: 'CNY',
  }
})

const references = new Map([
  [1, { ...skus[0], actual_quantity: '100.00', reserved_quantity: '30.00', available_quantity: '70.00', in_transit_quantity: '40.00' }],
  [2, { ...skus[1], actual_quantity: '20.00', reserved_quantity: '20.00', available_quantity: '0.00', in_transit_quantity: '5.00' }],
])

async function mockPurchaseApi(page) {
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    if (path === '/api/session/current-operator/') return route.fulfill({ json: { authenticated: true, development_superadmin: true, has_all_permissions: true, name: '库存差异验收' } })
    if (path === '/api/purchase-orders/' && route.request().method() === 'GET') return route.fulfill({ json: [] })
    if (path === '/api/suppliers/') return route.fulfill({ json: [{ id: 1, name: '库存差异验收供应商', payment_terms_config: [] }] })
    if (path === '/api/orders/') return route.fulfill({ json: [] })
    if (path === '/api/skus/' && route.request().method() === 'GET') return route.fulfill({ json: skus })
    const skuMatch = path.match(/^\/api\/skus\/(\d+)\/$/)
    if (skuMatch) {
      const id = Number(skuMatch[1])
      if (id === 1) await new Promise(resolve => setTimeout(resolve, 320))
      return route.fulfill({ json: references.get(id) || { ...skus[id - 1], actual_quantity: '0.00', reserved_quantity: '0.00', available_quantity: '0.00', in_transit_quantity: '0.00' } })
    }
    if (path === '/api/supplier-skus/') return route.fulfill({ json: [] })
    if (path === '/api/skus/1/inventory-detail/' || path === '/api/skus/2/inventory-detail/') {
      return route.fulfill({ json: {
        sku: { id: 1, sku: skus[0].sku, display_name_cn: skus[0].display_name_cn, unit: 'pcs' },
        movements: [{
          id: 11, movement_no: 'IM-FIX-001', movement_date: '2026-10-20', type_display: '采购入库', signed_quantity: '100.00',
          trade_unit: null, warehouse: '北区成品仓', source_no: 'PO-FIX-001', reference: 'PO-FIX-001', notes: '防潮袋；客户 LOGO 待确认',
          source_label: '当前供应来源档案',
          supplier_name: '库存差异验收供应商', supplier_model: 'IR-24W', supplier_sku_code: 'IR-FIX-001', supplier_characteristics: { 包装: '防潮袋', LOGO: '客户标记待确认' },
        }],
        purchases: [{ id: 21, purchase_no: 'PO-FIX-001', supplier_name: '库存差异验收供应商', status: 'ordered', status_display: '已下单', quantity: '100.00', received_quantity: '100.00', supplier_sources: [{ source_label: '历史采购来源快照', supplier_name: '库存差异验收供应商', supplier_model: 'IR-24W', supplier_sku_code: 'IR-FIX-001', characteristics: { 包装: '防潮袋', LOGO: '客户标记待确认' } }] }],
        orders: [], shipments: [],
      } })
    }
    return route.fulfill({ json: [] })
  })
}

async function openPurchaseEditor(page, width) {
  await page.setViewportSize({ width, height: 900 })
  await mockPurchaseApi(page)
  await page.goto('/purchase-orders?create=1')
  const dialog = page.getByRole('dialog', { name: '新建采购单' })
  await expect(dialog).toBeVisible()
  await dialog.getByLabel('供应商').selectOption('1')
  await expect(dialog.locator('.sku-picker-options label')).toHaveCount(12)
  return dialog
}

for (const width of [1440, 1024, 700]) {
  test(`采购 SKU 选择器与库存参考在 ${width}px 可操作`, async ({ page }) => {
    const dialog = await openPurchaseEditor(page, width)
    const picker = dialog.locator('.sku-selection-panel')
    const options = dialog.locator('.sku-picker-options')
    await expect(options).toBeVisible()
    const dimensions = await page.evaluate(() => ({ pageWidth: document.documentElement.scrollWidth, viewport: innerWidth }))
    expect(dimensions.pageWidth).toBeLessThanOrEqual(dimensions.viewport)
    expect(await options.evaluate(element => element.clientHeight)).toBeGreaterThanOrEqual(width === 700 ? 150 : 0)

    await picker.getByRole('checkbox', { name: /INV3-FIX-A/ }).check()
    await expect(dialog.locator('[data-testid="purchase-sku-reference"]')).toContainText('INV3-FIX-A')
    await expect(dialog.locator('.purchase-sku-metrics')).toContainText('100')
    const quantity = dialog.getByLabel(/采购数量/).first()
    await quantity.fill('12')

    await picker.getByRole('checkbox', { name: /INV3-FIX-B/ }).check()
    await expect(dialog.locator('.purchase-sku-reference')).toContainText('INV3-FIX-B')
    await expect(dialog.locator('.purchase-sku-metrics')).toContainText('20')
    await picker.getByRole('checkbox', { name: /INV3-FIX-B/ }).uncheck()
    await expect(dialog.locator('.purchase-line')).toHaveCount(1)
    await expect(dialog.locator('.purchase-sku-reference')).toContainText('INV3-FIX-A')
    expect(await dialog.locator('.purchase-line input').evaluateAll(inputs => inputs.map(input => input.value))).toContain('12')

    await dialog.getByRole('button', { name: '查看库存记录与差异' }).click()
    await expect(dialog.locator('.purchase-sku-difference')).toContainText('北区成品仓')
    await expect(dialog.locator('.purchase-sku-difference')).toContainText('PO-FIX-001')
    await expect(dialog.locator('.purchase-sku-difference')).toContainText('当前供应来源档案')
    await expect(dialog.locator('.purchase-sku-difference')).toContainText('历史采购来源快照')
    await expect(dialog.locator('.purchase-sku-difference')).toContainText('防潮袋')
    await expect(dialog.locator('.purchase-sku-difference')).toContainText('客户 LOGO 待确认')
  })
}

test('SKU 快速切换时迟到的库存响应不会覆盖当前 SKU', async ({ page }) => {
  const dialog = await openPurchaseEditor(page, 700)
  const picker = dialog.locator('.sku-selection-panel')
  await picker.getByRole('checkbox', { name: /INV3-FIX-A/ }).check()
  await picker.getByRole('checkbox', { name: /INV3-FIX-B/ }).check()
  await expect(dialog.locator('.purchase-sku-identity')).toContainText('INV3-FIX-B')
  await page.waitForTimeout(380)
  await expect(dialog.locator('.purchase-sku-identity')).toContainText('INV3-FIX-B')
  await expect(dialog.locator('.purchase-sku-metrics')).toContainText('20')
  await expect(dialog.locator('.purchase-sku-metrics')).not.toContainText('100')
})
