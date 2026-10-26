import { test, expect } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

const evidence = path.resolve(process.env.EVIDENCE_DIR || '../docs/uat-evidence/integration-020-022-051')
const evidenceTag = process.env.EVIDENCE_TAG || ''

const customer = { id: 1, name: 'Integration Buyer', country: 'Germany' }
const skus = [
  { id: 1, sku: 'INT-020-SKU-1', sku_code: 'INT-020-SKU-1', sales_model: 'INT-020-MODEL-1', display_name_cn: 'Integration Panel 1', product_name: 'Integration Panel 1', unit: 'pcs', active: true },
  { id: 2, sku: 'INT-020-SKU-2', sku_code: 'INT-020-SKU-2', sales_model: 'INT-020-MODEL-2', display_name_cn: 'Integration Panel 2', product_name: 'Integration Panel 2', unit: 'pcs', active: true },
]
const quote = {
  id: 1,
  quote_no: 'INT-020-1005',
  customer: 1,
  customer_name: customer.name,
  buyer_company_name: customer.name,
  recipient_name: 'Integration Recipient',
  buyer_address: 'Integration Address',
  buyer_email: 'integration@example.test',
  buyer_phone: '+49 1005',
  quote_date: '2026-10-26',
  valid_until: '2026-11-25',
  status: 'draft',
  status_display: '草稿',
  currency: 'EUR',
  exchange_rate: '7.800000',
  shipping_fee: '0.0250',
  discount: '0.0050',
  total_amount: '2.04',
  notes: '逐行分币舍入回归。',
  items: [
    { id: 1, sku: 1, sku_code: 'INT-020-SKU-1', sales_model_snapshot: 'INT-020-MODEL-1', product_name_snapshot: 'Integration Panel 1', unit_snapshot: 'pcs', quantity: '1.00', unit_price: '1.005000000000', amount: '1.01', description: 'Line 1', trade_snapshot: { unit: 'pcs', base_unit: 'pcs', factor: '1', name: '' } },
    { id: 2, sku: 2, sku_code: 'INT-020-SKU-2', sales_model_snapshot: 'INT-020-MODEL-2', product_name_snapshot: 'Integration Panel 2', unit_snapshot: 'pcs', quantity: '1.00', unit_price: '1.005000000000', amount: '1.01', description: 'Line 2', trade_snapshot: { unit: 'pcs', base_unit: 'pcs', factor: '1', name: '' } },
  ],
}
const workbench = { quote, root_quote_no: quote.quote_no, revisions: [quote], orders: [], important_notes: [], order_summary: { count: 0 } }
const pi = {
  invoice_no: quote.quote_no,
  buyer: { company_name: quote.buyer_company_name, name: quote.recipient_name, address: quote.buyer_address, email: quote.buyer_email, phone: quote.buyer_phone },
  terms: { quote_date: quote.quote_date, valid_until: quote.valid_until, lead_time_days: null, trading_terms: '', shipping_details: '', notes: quote.notes },
  totals: { currency: 'EUR', subtotal: '2.02', shipping_fee: '0.03', discount: '0.01', total_amount: '2.04' },
  payment_splits: { deposit_ratio: '0.3000', deposit_amount: '0.61', balance_ratio: '0.7000', balance_amount: '1.43' },
  products: quote.items.map(item => ({ ...item, model: item.sales_model_snapshot, product_name: item.product_name_snapshot, display_name: item.product_name_snapshot, base_quantity: item.quantity, unit_price: item.unit_price, amount: item.amount, unit: item.unit_snapshot })),
}

test('Chrome quote workbench and saved PI show the reconciled 1.005 total', async ({ page }) => {
  await fs.mkdir(evidence, { recursive: true })
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const method = route.request().method()
    if (url.pathname === '/api/session/current-operator/') return route.fulfill({ json: { authenticated: true, development_superadmin: true, has_all_permissions: true, name: '集成验收' } })
    if (url.pathname === '/api/quotes/1/workbench/') return route.fulfill({ json: workbench })
    if (url.pathname === '/api/quotes/1/pi-data/') return route.fulfill({ json: pi })
    if (url.pathname === '/api/quotes/' && method === 'GET') return route.fulfill({ json: [quote] })
    if (url.pathname === '/api/customers/' && method === 'GET') return route.fulfill({ json: [customer] })
    if (url.pathname === '/api/skus/' && method === 'GET') return route.fulfill({ json: skus })
    if (url.pathname === '/api/operation-logs/' && method === 'GET') return route.fulfill({ json: [] })
    return route.fulfill({ json: [] })
  })

  await page.setViewportSize({ width: 1440, height: 1100 })
  await page.goto('/quotes?detail=1')
  const detail = page.getByRole('dialog', { name: '报价工作台' })
  await expect(detail).toBeVisible()
  await expect(detail).toContainText('EUR 2.04')
  await expect(detail).toContainText('Integration Buyer')
  await page.screenshot({ path: path.join(evidence, `chrome-quote-workbench-1440${evidenceTag}.png`), fullPage: true })

  await detail.getByRole('button', { name: '预览 PI', exact: true }).first().click()
  const preview = page.getByRole('dialog', { name: '报价单预览' })
  await expect(preview).toBeVisible()
  await expect(preview).toContainText('Grand Total')
  await expect(preview).toContainText('2.04')
  await page.screenshot({ path: path.join(evidence, `chrome-quote-pi-1440${evidenceTag}.png`), fullPage: true })

  await page.setViewportSize({ width: 700, height: 1000 })
  await page.screenshot({ path: path.join(evidence, `chrome-quote-pi-700${evidenceTag}.png`), fullPage: true })
})
