import { expect, test } from '@playwright/test'
import path from 'node:path'

const evidenceDir = path.resolve(process.cwd(), '../docs/uat-evidence/r1-sku-01-fix-01')

const customer = { id: 1, name: 'R1_FIX 客户' }
const sku = {
  id: 7,
  sku: 'SKU-R1-FIX',
  sku_code: 'SKU-R1-FIX',
  display_name_cn: 'R1 修复测试灯具',
  product_name: 'R1 修复测试灯具',
  product: 1,
  product_name: 'R1 修复测试灯具',
  sales_model: '',
  unit: 'pcs',
  currency: 'USD',
  default_price: '100.00',
  active: true,
  category_names: ['照明'],
  packaging: {},
}

function quote(id, quoteNo, overrides = {}) {
  return {
    id,
    quote_no: quoteNo,
    customer: customer.id,
    customer_name: customer.name,
    quote_date: '2026-10-20',
    valid_until: '2026-11-19',
    updated_at: '2026-10-20T10:00:00Z',
    status: 'draft',
    status_display: '草稿',
    currency: 'USD',
    exchange_rate: '7.2',
    total_amount: '200.00',
    parent_quote: null,
    root_quote: null,
    revision_no: 0,
    revision_summary: '',
    items: [{
      id: id * 10,
      sku: sku.id,
      sku_code: sku.sku_code,
      model: '',
      sales_model_snapshot: '',
      product_name: sku.product_name,
      display_name_snapshot: sku.display_name_cn,
      description_snapshot: 'R1 fixture',
      quantity: '2',
      trade_quantity: '2',
      unit: 'pcs',
      trade_unit: 'pcs',
      unit_price: '100.00',
      trade_unit_price: '100.00',
      amount: '200.00',
      trade_snapshot: { unit: 'pcs', base_unit: 'pcs', factor: '1', name: '件' },
    }],
    ...overrides,
  }
}

async function setupQuoteFixture(page) {
  const state = {
    rows: [quote(1, 'QA-Q001')],
    operator: { name: 'R1 FIX fixture', development_superadmin: true, has_all_permissions: true },
    risk: 'risk',
    exportFailuresRemaining: 0,
    exportCount: 0,
    riskRequests: 0,
    createdCount: 0,
  }
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const pathName = url.pathname
    const method = route.request().method()
    if (pathName === '/api/session/current-operator/') return route.fulfill({ json: state.operator })
    if (pathName === '/api/customers/') return route.fulfill({ json: [customer] })
    if (pathName === '/api/skus/') return route.fulfill({ json: [sku] })
    if (pathName === '/api/packaging-templates/') return route.fulfill({ json: [] })
    if (pathName === '/api/quotes/' && method === 'GET') return route.fulfill({ json: state.rows })
    if (pathName === '/api/quotes/risk-preview/' && method === 'GET') {
      state.riskRequests += 1
      if (state.risk === 'unavailable') return route.fulfill({ status: 503, json: { detail: '风险检查服务不可用' } })
      return route.fulfill({ json: { items: state.risk === 'risk' ? [{ sku: sku.id, sku_code: sku.sku_code, label: sku.display_name_cn, has_risk: true, risk_labels: ['缺少 Sales Model', '缺少有效采购参考成本'] }] : [] } })
    }
    if (pathName === '/api/sales-rules/check-quote/' && method === 'POST') return route.fulfill({ json: [] })
    if (pathName === '/api/quotes/availability-preview/' && method === 'POST') return route.fulfill({ json: { items: [] } })
    if (pathName === '/api/quotes/' && method === 'POST') {
      const data = route.request().postDataJSON()
      const created = quote(2 + state.createdCount, `QA-Q00${2 + state.createdCount}`, { items: data.items || [], total_amount: '100.00' })
      state.createdCount += 1
      state.rows.push(created)
      return route.fulfill({ json: created })
    }
    if (/^\/api\/quotes\/1\/revise\/$/.test(pathName) && method === 'POST') {
      const data = route.request().postDataJSON()
      const revised = quote(9, 'QA-Q001-R1', { parent_quote: 1, root_quote: 1, revision_no: 1, revision_summary: data.revision_summary, items: data.items || [] })
      state.rows.push(revised)
      return route.fulfill({ json: revised })
    }
    if (/^\/api\/quotes\/\d+\/$/.test(pathName) && method === 'GET') {
      const id = Number(pathName.split('/')[3])
      return route.fulfill({ json: state.rows.find(row => row.id === id) || state.rows[0] })
    }
    if (/^\/api\/quotes\/\d+\/workbench\/$/.test(pathName) && method === 'GET') {
      const id = Number(pathName.split('/')[3])
      const current = state.rows.find(row => row.id === id) || state.rows[0]
      return route.fulfill({ json: { quote: current, root_quote_no: state.rows.find(row => row.id === (current.root_quote || current.id))?.quote_no || current.quote_no, revisions: state.rows, orders: [], important_notes: [] } })
    }
    if (/^\/api\/quotes\/\d+\/export\/$/.test(pathName) && method === 'GET') {
      state.exportCount += 1
      if (state.exportFailuresRemaining > 0) {
        state.exportFailuresRemaining -= 1
        return route.fulfill({ status: 503, json: { detail: 'Excel 导出服务暂时不可用' } })
      }
      return route.fulfill({ status: 200, contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', body: 'PK\u0003\u0004R1-FIX' })
    }
    return route.fulfill({ json: [] })
  })
  return state
}

test('quote list risk confirmation, cancellation and retry re-check', async ({ page }) => {
  const state = await setupQuoteFixture(page)
  await page.goto('/quotes')
  await expect(page.getByRole('button', { name: '导出 QA-Q001', exact: true })).toBeVisible()

  await page.getByRole('button', { name: '导出 QA-Q001', exact: true }).click()
  const risk = page.locator('.quote-risk-modal')
  await expect(risk).toContainText('缺少 Sales Model')
  await expect(risk).toContainText('缺少有效采购参考成本')
  await page.screenshot({ path: path.join(evidenceDir, 'quote-risk-confirmation.png') })
  await risk.getByRole('button', { name: '暂不导出', exact: true }).click()
  await expect(risk).toHaveCount(0)
  expect(state.exportCount).toBe(0)

  state.risk = 'none'
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: '导出 QA-Q001', exact: true }).click()
  expect((await download).suggestedFilename()).toBe('QA-Q001.xlsx')
  expect(state.riskRequests).toBe(2)
})

test('risk service outage requires active confirmation and failed export retry stays checked', async ({ page }) => {
  const state = await setupQuoteFixture(page)
  state.risk = 'unavailable'
  await page.goto('/quotes')
  await page.getByRole('button', { name: '导出 QA-Q001', exact: true }).click()
  const risk = page.locator('.quote-risk-modal')
  await expect(risk).toContainText('风险检查服务暂时不可用', { timeout: 15000 })
  await expect(risk).toContainText('这不代表报价无风险')
  await page.screenshot({ path: path.join(evidenceDir, 'quote-risk-unavailable.png') })
  const confirmedDownload = page.waitForEvent('download')
  await risk.getByRole('button', { name: '了解风险，继续导出', exact: true }).click()
  expect((await confirmedDownload).suggestedFilename()).toBe('QA-Q001.xlsx')

  state.risk = 'none'
  state.exportFailuresRemaining = 6
  await page.getByRole('button', { name: '导出 QA-Q001', exact: true }).click()
  await expect(page.locator('.toast')).toContainText('导出 QA-Q001 失败', { timeout: 20000 })
  await page.screenshot({ path: path.join(evidenceDir, 'quote-export-failed-retry.png') })
  const retryDownload = page.waitForEvent('download')
  await page.getByRole('button', { name: '导出 QA-Q001', exact: true }).click()
  expect((await retryDownload).suggestedFilename()).toBe('QA-Q001.xlsx')
  expect(state.riskRequests).toBeGreaterThanOrEqual(3)
})

test('new and revised quote save-export keep editor open until risk decision', async ({ page }) => {
  const state = await setupQuoteFixture(page)
  await page.goto('/quotes?create=1')
  const editor = page.locator('.quote-editor-modal')
  await expect(editor).toBeVisible()
  await editor.locator('select').first().selectOption(String(customer.id))
  await editor.locator('.sku-picker-options input[type="checkbox"]').first().check()
  await expect(editor.locator('.quote-line-row')).toHaveCount(1)
  await editor.getByRole('button', { name: '保存并导出 Excel', exact: true }).click()
  const createRisk = page.locator('.quote-risk-modal')
  await expect(createRisk).toBeVisible()
  await expect(editor).toBeVisible()
  await page.screenshot({ path: path.join(evidenceDir, 'quote-save-risk-create.png') })
  await createRisk.getByRole('button', { name: '暂不导出', exact: true }).click()
  await expect(editor).toHaveCount(0)
  await expect(page.locator('.quote-table')).toContainText('QA-Q002')
  await page.getByRole('button', { name: '关闭报价详情', exact: true }).click()

  await page.getByRole('button', { name: '创建修订版 QA-Q001', exact: true }).click()
  const revisionEditor = page.locator('.quote-editor-modal')
  await expect(revisionEditor).toBeVisible()
  await expect(revisionEditor).toContainText('创建报价修订版')
  await revisionEditor.locator('.revision-summary textarea').fill('调整交期与报价说明')
  await revisionEditor.getByRole('button', { name: '保存并导出 Excel', exact: true }).click()
  const revisionRisk = page.locator('.quote-risk-modal')
  await expect(revisionRisk).toBeVisible()
  await expect(revisionEditor).toBeVisible()
  const revisionDownload = page.waitForEvent('download')
  await revisionRisk.getByRole('button', { name: '了解风险，继续导出', exact: true }).click()
  expect((await revisionDownload).suggestedFilename()).toBe('QA-Q001-R1.xlsx')
  await expect(revisionEditor).toHaveCount(0)
})

async function setupSkuCostFixture(page) {
  const state = {
    operator: { name: 'R1 SKU fixture', development_superadmin: true, has_all_permissions: true },
    row: {
      ...sku,
      cost_price: '8.00',
      cost_currency: 'USD',
      cost_verification_state: 'current',
      cost_verified_at: '2026-10-01T08:00:00Z',
      cost_verified_by_name: '采购 fixture',
      stock_quantity: '0',
    },
    sources: [{
      id: 1,
      sku: sku.id,
      supplier: 2,
      supplier_name: 'R1 供应商',
      supplier_sku_code: 'SUP-R1-FIX',
      supplier_model: 'SUP-MODEL-R1',
      purchase_price: '6.00',
      currency: 'USD',
      purchase_price_verification_state: 'current',
      purchase_price_verified_at: '2026-10-01T08:00:00Z',
      purchase_price_verified_by_name: '采购 fixture',
      moq: 1,
      lead_time_days: 7,
      is_active: true,
      is_preferred: true,
    }],
    verifyCalls: [],
  }
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const pathName = url.pathname
    const method = route.request().method()
    if (pathName === '/api/session/current-operator/') return route.fulfill({ json: state.operator })
    if (pathName === '/api/products/') return route.fulfill({ json: [{ id: 1, code: 'P-R1', name: 'R1 产品', category: 1, sales_model_prefix: 'R1' }] })
    if (pathName === '/api/categories/tree/') return route.fulfill({ json: [{ id: 1, name: '照明', attributes: [], effective_attributes: [] }] })
    if (pathName === '/api/suppliers/') return route.fulfill({ json: [{ id: 2, name: 'R1 供应商' }] })
    if (pathName === '/api/skus/' && method === 'GET') return route.fulfill({ json: [state.row] })
    if (pathName === '/api/skus/7/' && method === 'GET') return route.fulfill({ json: state.row })
    if (pathName === '/api/supplier-skus/' && method === 'GET') return route.fulfill({ json: state.sources })
    if ((pathName.includes('/verify-cost/') || pathName.includes('/verify-price/')) && method === 'POST') {
      state.verifyCalls.push(pathName)
      return route.fulfill({ json: state.row })
    }
    return route.fulfill({ json: [] })
  })
  return state
}

test('SKU browser flow blocks unsaved and invalid cost verification', async ({ page }) => {
  const state = await setupSkuCostFixture(page)
  await page.goto('/skus')
  await page.locator('.sku-data-row').filter({ hasText: 'SKU-R1-FIX' }).getByRole('button', { name: '编辑', exact: true }).click()
  const editor = page.getByRole('dialog', { name: '编辑 SKU', exact: true })
  await expect(editor).toBeVisible()
  await editor.locator('.sku-cost-field input').fill('9.00')
  await editor.getByRole('button', { name: '确认价格仍有效', exact: true }).first().click()
  await expect(page.getByRole('status')).toContainText('请先保存当前 SKU 成本价格和成本币种')
  expect(state.verifyCalls).toHaveLength(0)
  await page.screenshot({ path: path.join(evidenceDir, 'sku-unsaved-cost-blocked.png') })

  state.row = { ...state.row, cost_price: '0.00', cost_currency: '', cost_verification_state: 'current' }
  state.sources = [{ ...state.sources[0], purchase_price: '0.00', currency: '', purchase_price_verification_state: 'current' }]
  await page.reload()
  await page.locator('.sku-data-row').filter({ hasText: 'SKU-R1-FIX' }).getByRole('button', { name: '编辑', exact: true }).click()
  const invalidEditor = page.getByRole('dialog', { name: '编辑 SKU', exact: true })
  await invalidEditor.getByRole('button', { name: '确认价格仍有效', exact: true }).first().click()
  await expect(page.getByRole('status')).toContainText('SKU 内部成本必须大于 0 且成本币种已维护')
  await invalidEditor.locator('.supplier-source-table tbody tr').first().getByRole('button', { name: '确认价格仍有效', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('采购参考价必须大于 0 且采购币种已维护')
  expect(state.verifyCalls).toHaveLength(0)
  await page.screenshot({ path: path.join(evidenceDir, 'sku-invalid-cost-blocked.png') })
})

test('sales user sees generic quote risks without purchasing prices', async ({ page }) => {
  const state = await setupQuoteFixture(page)
  state.operator = { name: 'R1 销售 fixture', authenticated: true, rbac_enforcement: true, permissions: { quotes: { view: true, export: true }, skus: { view: true } } }
  await page.goto('/quotes')
  await page.getByRole('button', { name: '导出 QA-Q001', exact: true }).click()
  const risk = page.locator('.quote-risk-modal')
  await expect(risk).toContainText('缺少 Sales Model')
  await expect(risk).toContainText('缺少有效采购参考成本')
  await expect(risk).not.toContainText('100.00')
  await expect(risk).not.toContainText('6.00')
  await page.screenshot({ path: path.join(evidenceDir, 'quote-risk-sales-no-cost.png') })
  await risk.getByRole('button', { name: '暂不导出', exact: true }).click()
})

test('SKU page hides purchasing amounts for a sales-only user', async ({ page }) => {
  const state = await setupSkuCostFixture(page)
  state.operator = { name: 'R1 销售 SKU fixture', authenticated: true, rbac_enforcement: true, permissions: { skus: { view: true, update: true }, products: { view: true }, suppliers: { view: true, update: true }, purchases: { view: false, update: false } } }
  await page.goto('/skus')
  await page.locator('.sku-data-row').filter({ hasText: 'SKU-R1-FIX' }).getByRole('button', { name: '编辑', exact: true }).click()
  const editor = page.getByRole('dialog', { name: '编辑 SKU', exact: true })
  await expect(editor.locator('.sku-cost-field')).toHaveCount(0)
  await expect(editor.locator('.supplier-source-table')).toContainText('采购价已隐藏')
  await expect(editor.locator('.supplier-source-table').getByRole('button', { name: '确认价格仍有效', exact: true })).toHaveCount(0)
  await page.screenshot({ path: path.join(evidenceDir, 'sku-purchase-price-hidden.png') })
})
