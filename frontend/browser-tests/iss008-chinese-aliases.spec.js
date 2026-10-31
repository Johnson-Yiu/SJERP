import { expect, test } from '@playwright/test'
import path from 'node:path'

const evidenceDir = process.env.ISS008_FUP_01_EVIDENCE_DIR ? path.resolve(process.env.ISS008_FUP_01_EVIDENCE_DIR) : null
const catalog = [
  { value: 'DE', label: 'Germany / DE', nameZh: '德国', searchText: 'Germany 德国 DE DEU' },
  { value: 'US', label: 'United States / US', nameZh: '美国', searchText: 'United States 美国 US USA united states of america' },
  { value: 'HK', label: 'Hong Kong / HK', nameZh: '中国香港特别行政区', searchText: 'Hong Kong 中国香港特别行政区 香港 HK HKG' },
  { value: 'MO', label: 'Macao / MO', nameZh: '中国澳门特别行政区', searchText: 'Macao 中国澳门特别行政区 澳门 MO MAC' },
  { value: 'CD', label: 'Congo, The Democratic Republic of the / CD', nameZh: '刚果（金）', searchText: 'Congo Democratic Republic 刚果（金）刚果民主共和国 CD COD' },
  { value: 'CG', label: 'Congo / CG', nameZh: '刚果（布）', searchText: 'Congo 刚果（布）刚果共和国 CG COG' },
]

const customer = {
  id: 1,
  name: '中文国家选择客户',
  code: 'C-ISS008-FUP',
  country: 'DE',
  country_display: 'Germany / DE',
  status: 'customer',
  owner: '开发验收',
  contacts: [],
}

const sku = { id: 1, code: 'SKU-ISS008', name: '国家选择验收灯具', display_name: 'SKU-ISS008 · 国家选择验收灯具', unit: 'pcs', base_unit: 'pcs' }

async function mockApi(page) {
  const writes = { created: [], updated: [] }
  let customerRecord = { ...customer }
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const endpoint = url.pathname
    const method = route.request().method()
    if (endpoint === '/api/session/current-operator/') return route.fulfill({ json: { authenticated: true, development_superadmin: true, has_all_permissions: true, name: '开发验收' } })
    if (endpoint === '/api/customers/country-catalog/') return route.fulfill({ json: catalog })
    if (endpoint === '/api/customers/owner-options/') return route.fulfill({ json: [] })
    if (endpoint === '/api/customers/' && method === 'GET') return route.fulfill({ json: [customerRecord] })
    if (endpoint === '/api/customers/' && method === 'POST') {
      writes.created.push(route.request().postDataJSON())
      return route.fulfill({ status: 201, json: { ...customerRecord, ...writes.created.at(-1), id: 2 } })
    }
    if (endpoint === '/api/customers/1/' && method === 'PUT') {
      writes.updated.push(route.request().postDataJSON())
      customerRecord = { ...customerRecord, ...writes.updated.at(-1), country_display: writes.updated.at(-1).country === 'HK' ? 'Hong Kong / HK' : 'Germany / DE' }
      return route.fulfill({ json: customerRecord })
    }
    if (endpoint === '/api/quotes/' && method === 'GET') return route.fulfill({ json: [] })
    if (endpoint === '/api/quotes/' && method === 'POST') return route.fulfill({ status: 201, json: { id: 2, quote_no: 'SJ20261028DE001', customer: 1, status: 'draft' } })
    if (endpoint === '/api/skus/' && method === 'GET') return route.fulfill({ json: [sku] })
    if (endpoint === '/api/categories/tree/') return route.fulfill({ json: [] })
    return route.fulfill({ json: [] })
  })
  return writes
}

for (const width of [1440, 390]) {
  test(`customer edit, country aliases and quote customer picker remain usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 })
    const writes = await mockApi(page)

    await page.goto('/customers')
    await expect(page.locator('.data-table tbody')).toContainText('中文国家选择客户')

    await page.getByRole('button', { name: '编辑', exact: true }).click()
    const editDialog = page.locator('form.customer-editor')
    const editCountry = editDialog.locator('input[placeholder="搜索名称、中文或代码后选择"]')
    await expect(editCountry).toHaveValue('Germany / DE')
    await editCountry.fill('中国香港')
    await expect(editDialog.getByRole('button', { name: /Hong Kong \/ HK/ })).toBeVisible()
    await editDialog.getByRole('button', { name: /Hong Kong \/ HK/ }).click()
    await expect(editCountry).toHaveValue('Hong Kong / HK')
    if (evidenceDir) await page.screenshot({ path: path.join(evidenceDir, `customer-edit-country-${width}.png`), fullPage: true })
    await editDialog.getByRole('button', { name: '保存客户', exact: true }).click()
    await expect.poll(() => writes.updated.at(-1)?.country).toBe('HK')
    await page.reload()
    await page.getByRole('button', { name: '编辑', exact: true }).click()
    const reloadedEditDialog = page.locator('form.customer-editor')
    await expect(reloadedEditDialog.locator('input[placeholder="搜索名称、中文或代码后选择"]')).toHaveValue('Hong Kong / HK')
    await reloadedEditDialog.locator('.modal-head button').click()

    await page.getByRole('button', { name: '新建客户', exact: true }).click()
    const customerDialog = page.locator('form.customer-editor')
    const country = customerDialog.locator('input[placeholder="搜索名称、中文或代码后选择"]')
    await country.fill('德国')
    await expect(customerDialog.getByRole('button', { name: /Germany \/ DE/ })).toBeVisible()
    await customerDialog.getByRole('button', { name: /Germany \/ DE/ }).click()
    await expect(country).toHaveValue('Germany / DE')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    if (evidenceDir) await page.screenshot({ path: path.join(evidenceDir, `customer-country-${width}.png`), fullPage: true })
    await customerDialog.getByRole('button', { name: '取消', exact: true }).click()

    await page.goto('/quotes')
    await page.getByRole('button', { name: '新建报价', exact: true }).click()
    const quoteDialog = page.locator('form.quote-editor-modal')
    const quoteCustomer = quoteDialog.locator('select').first()
    await expect(quoteCustomer.locator('option[value="1"]')).toHaveText('中文国家选择客户')
    await quoteCustomer.selectOption('1')
    await expect(quoteCustomer).toHaveValue('1')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    if (evidenceDir) await page.screenshot({ path: path.join(evidenceDir, `quote-customer-${width}.png`), fullPage: true })
  })
}
