import fs from 'node:fs/promises'
import path from 'node:path'
import playwright from '../../../frontend/node_modules/playwright/index.js'

const { chromium } = playwright

const outputDir = path.resolve(process.cwd(), 'docs/uat-evidence/r1-inv-03-fix-01')
const baseUrl = 'http://127.0.0.1:5195'
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

async function mockApi(page) {
  await page.route('**/api/**', async route => {
    const pathName = new URL(route.request().url()).pathname
    if (pathName === '/api/session/current-operator/') return route.fulfill({ json: { authenticated: true, development_superadmin: true, has_all_permissions: true, name: '库存差异验收' } })
    if (pathName === '/api/purchase-orders/' && route.request().method() === 'GET') return route.fulfill({ json: [] })
    if (pathName === '/api/suppliers/') return route.fulfill({ json: [{ id: 1, name: '库存差异验收供应商', payment_terms_config: [] }] })
    if (pathName === '/api/orders/') return route.fulfill({ json: [] })
    if (pathName === '/api/skus/' && route.request().method() === 'GET') return route.fulfill({ json: skus })
    const skuMatch = pathName.match(/^\/api\/skus\/(\d+)\/$/)
    if (skuMatch) return route.fulfill({ json: references.get(Number(skuMatch[1])) || { ...skus[Number(skuMatch[1]) - 1], actual_quantity: '0.00', reserved_quantity: '0.00', available_quantity: '0.00', in_transit_quantity: '0.00' } })
    if (pathName === '/api/supplier-skus/') return route.fulfill({ json: [] })
    if (pathName.endsWith('/inventory-detail/')) return route.fulfill({ json: {
      sku: { id: 1, sku: skus[0].sku, display_name_cn: skus[0].display_name_cn, unit: 'pcs' },
      movements: [{ id: 11, movement_no: 'IM-FIX-001', movement_date: '2026-10-20', type_display: '采购入库', signed_quantity: '100.00', warehouse: '北区成品仓', source_no: 'PO-FIX-001', reference: 'PO-FIX-001', notes: '防潮袋；客户 LOGO 待确认', supplier_name: '库存差异验收供应商', supplier_model: 'IR-24W', supplier_sku_code: 'IR-FIX-001', supplier_characteristics: { 包装: '防潮袋', LOGO: '客户标记待确认' } }],
      purchases: [{ id: 21, purchase_no: 'PO-FIX-001', supplier_name: '库存差异验收供应商', status: 'ordered', status_display: '已下单', quantity: '100.00', received_quantity: '100.00', supplier_sources: [{ supplier_name: '库存差异验收供应商', supplier_model: 'IR-24W', supplier_sku_code: 'IR-FIX-001', characteristics: { 包装: '防潮袋', LOGO: '客户标记待确认' } }] }],
      orders: [], shipments: [],
    } })
    return route.fulfill({ json: [] })
  })
}

await fs.mkdir(outputDir, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const log = []
for (const width of [1440, 1024, 700]) {
  const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 1 })
  await mockApi(page)
  await page.goto(`${baseUrl}/purchase-orders?create=1`, { waitUntil: 'networkidle' })
  const dialog = page.getByRole('dialog', { name: '新建采购单' })
  await dialog.getByLabel('供应商').selectOption('1')
  const picker = dialog.locator('.sku-selection-panel')
  await picker.getByRole('checkbox', { name: /INV3-FIX-A/ }).check()
  await picker.getByRole('checkbox', { name: /INV3-FIX-B/ }).check()
  await dialog.locator('[data-testid="purchase-sku-reference"] .purchase-sku-metrics').waitFor({ state: 'visible' })
  await page.screenshot({ path: path.join(outputDir, `purchase-sku-picker-${width}.png`), fullPage: false })
  const layout = await page.evaluate(() => {
    const options = document.querySelector('.sku-picker-options')
    const panel = document.querySelector('.sku-selection-panel')
    return { viewport: innerWidth, pageWidth: document.documentElement.scrollWidth, optionsHeight: options?.clientHeight, optionsScrollHeight: options?.scrollHeight, panelHeight: panel?.getBoundingClientRect().height }
  })
  await dialog.getByRole('button', { name: '查看库存记录与差异' }).click()
  const difference = dialog.locator('.purchase-sku-difference')
  await difference.scrollIntoViewIfNeeded()
  await page.screenshot({ path: path.join(outputDir, `purchase-sku-difference-${width}.png`), fullPage: false })
  log.push({ width, selectedSku: await dialog.locator('.purchase-sku-identity').innerText(), inventoryReference: await dialog.locator('.purchase-sku-metrics').innerText(), layout })
  await page.close()
}
await browser.close()
await fs.writeFile(path.join(outputDir, 'browser-capture-log.json'), `${JSON.stringify(log, null, 2)}\n`, 'utf8')
console.log(JSON.stringify(log, null, 2))
