import { test, expect } from '@playwright/test'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { randomUUID } from 'node:crypto'

const baseURL = process.env.ISOLATED_PLAYWRIGHT_BASE_URL
const evidenceDir = path.resolve(process.env.ISS028_035_EVIDENCE_DIR || '../docs/uat-evidence/r1-iss028-035-category-verify-bd324-20261031/browser')
const pythonInspector = path.resolve('../docs/uat-evidence/r1-iss028-035-category-verify-bd324-20261031/inspect_fixture_sqlite.py')
const httpResults = []
const layoutResults = []

fs.mkdirSync(evidenceDir, { recursive: true })

function apiURL(route) {
  return new URL(`/api${route}`, baseURL).toString()
}

async function api(page, method, route, data, expectedStatus = 200) {
  const options = data === undefined ? {} : { data }
  const response = await page.request[method](apiURL(route), options)
  const text = await response.text()
  let body
  try { body = text ? JSON.parse(text) : null } catch { body = text }
  httpResults.push({ method: method.toUpperCase(), path: `/api${route}`, status: response.status(), result: typeof body === 'string' ? body : body })
  expect(response.status(), `${method.toUpperCase()} /api${route}: ${text}`).toBe(expectedStatus)
  return body
}

function stamp() {
  return randomUUID().replaceAll('-', '').slice(0, 8).toUpperCase()
}

function saveJson(name, value) {
  fs.writeFileSync(path.join(evidenceDir, name), `${JSON.stringify(value, null, 2)}\n`, 'utf8')
}

function inspectDatabase(ids) {
  const dbPath = path.resolve(process.env.ISOLATED_TEST_DATABASE || '')
  const root = path.resolve(process.env.ISOLATED_TEST_ROOT || '')
  expect(root).not.toBe(path.parse(root).root)
  expect(dbPath.startsWith(`${root}${path.sep}`)).toBe(true)
  const result = spawnSync(process.env.ISOLATED_TEST_PYTHON || 'python', [pythonInspector, JSON.stringify(ids)], {
    cwd: path.resolve('../backend'),
    encoding: 'utf8',
    env: process.env,
  })
  expect(result.status, result.stderr || result.stdout).toBe(0)
  return JSON.parse(result.stdout)
}

async function selectCategoryNode(page, name) {
  await page.getByLabel('搜索分类').fill(name)
  const node = page.locator('.tree-node').filter({ has: page.getByText(name, { exact: true }) }).first()
  await expect(node).toBeVisible()
  await node.click()
  return node
}

async function assignRootCategory(page, product, rootId, rootName, width, screenshotName) {
  const height = width === 390 ? 844 : 960
  await page.setViewportSize({ width, height })
  await page.goto('/products')
  const row = page.locator('.product-list-table tbody tr').filter({ hasText: product.name })
  await expect(row).toBeVisible()
  await row.getByRole('button', { name: '编辑产品' }).click()
  const editor = page.getByRole('dialog', { name: '编辑产品' })
  await expect(editor).toBeVisible()
  const primaryCategory = editor.locator('.category-select').first()
  await primaryCategory.click()
  const rootChoice = editor.getByRole('button', { name: `选择分类 ${rootName}`, exact: true })
  await expect(rootChoice).toBeVisible()
  await rootChoice.click()
  await expect(primaryCategory).toContainText(rootName)
  await page.screenshot({ path: path.join(evidenceDir, screenshotName), fullPage: true })
  await editor.getByRole('button', { name: '保存', exact: true }).click()
  await expect(editor).toBeHidden()
  const saved = await api(page, 'get', `/products/${product.id}/`)
  expect(saved.category).toBe(rootId)
  expect(saved.category_name).toBe(rootName)
  const layout = await page.evaluate(() => ({
    viewport: innerWidth,
    page: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }))
  expect(layout.page).toBeLessThanOrEqual(layout.viewport)
  expect(layout.body).toBeLessThanOrEqual(layout.viewport)
  return { saved, layout }
}

async function measureCategoryLayout(page) {
  return page.evaluate(() => {
    const rect = selector => {
      const element = document.querySelector(selector)
      if (!element) return null
      const box = element.getBoundingClientRect()
      return { left: box.left, top: box.top, right: box.right, bottom: box.bottom, width: box.width, height: box.height }
    }
    const tree = rect('.tree-panel')
    const config = rect('.config-panel')
    const overlaps = tree && config && tree.left < config.right && tree.right > config.left && tree.top < config.bottom && tree.bottom > config.top
    return {
      viewport: innerWidth,
      page: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
      tree,
      config,
      treeConfigOverlap: Boolean(overlaps),
    }
  })
}

test.beforeEach(async ({ page, browser }) => {
  expect(process.env.PLAYWRIGHT_CHANNEL, '真实 Chrome 必须由 Playwright chrome channel 启动').toBe('chrome')
  const userAgent = await page.evaluate(() => navigator.userAgent)
  expect(userAgent).toContain('Chrome/')
  const environment = {
    product: 'Google Chrome',
    channel: process.env.PLAYWRIGHT_CHANNEL,
    playwrightBrowserType: browser.browserType().name(),
    browserVersion: browser.version(),
    userAgent,
  }
  saveJson('browser-environment.json', environment)
  console.log(`Real browser: ${environment.product} ${environment.browserVersion} (${environment.channel})`)
})

test.describe('ISS-028 / ISS-035 分类模板与 SKU 历史边界', () => {
  test('ISS-028 根/子分类归类、继承属性和筛选', async ({ page }) => {
    const id = stamp()
    const rootName = `验收${id}根分类`
    const childName = `验收${id}子分类`
    const root = await api(page, 'post', '/categories/', { name: rootName, description: '合成分类验证' }, 201)
    const child = await api(page, 'post', '/categories/', { name: childName, parent: root.id, description: '合成子分类验证' }, 201)
    await api(page, 'post', '/category-attributes/', {
      category: root.id, name: `电压${id}`, key: `voltage_${id.toLowerCase()}`, default_value: '24V', unit: 'V', include_in_sku: true,
    }, 201)
    await api(page, 'post', '/category-attributes/', {
      category: child.id, name: `色温${id}`, key: `cct_${id.toLowerCase()}`, default_value: '4000K', unit: 'K', include_in_sku: true,
    }, 201)

    const makeProduct = (name, category, prefixSuffix) => api(page, 'post', '/products/', {
      name, name_en: 'Synthetic category verification product', sales_model_prefix: `T${id}${prefixSuffix}`,
      category, status: 'active', description: 'Synthetic UAT data only',
    }, 201)
    const editableDesktop = await makeProduct(`验收${id}桌面待改分类产品`, child.id, 'E')
    const editableMobile = await makeProduct(`验收${id}窄屏待改分类产品`, child.id, 'M')
    const rootProduct = await makeProduct(`验收${id}根分类产品`, root.id, 'R')
    const childProduct = await makeProduct(`验收${id}子分类产品`, child.id, 'C')
    const childRead = await api(page, 'get', `/categories/${child.id}/`)
    const inherited = childRead.effective_attributes.find(attribute => attribute.key === `voltage_${id.toLowerCase()}`)
    expect(inherited).toMatchObject({ inherited: true, source_category: rootName, include_in_sku: true })

    const desktopAssignment = await assignRootCategory(page, editableDesktop, root.id, rootName, 1440, '01-iss028-root-category-assignment-desktop.png')
    layoutResults.push({ scenario: 'root-category-assignment-desktop', ...desktopAssignment.layout })
    await expect(page.locator('.page-head h2')).toHaveText('产品管理')

    const rootFilter = page.getByLabel('产品分类筛选')
    await rootFilter.selectOption(String(root.id))
    await expect(page).toHaveURL(new RegExp(`[?&]category=${root.id}(?:&|$)`))
    const rootRows = page.locator('.product-list-table tbody tr')
    await expect(rootRows).toHaveCount(2)
    await expect(rootRows.filter({ hasText: editableDesktop.name })).toBeVisible()
    await expect(rootRows.filter({ hasText: rootProduct.name })).toBeVisible()
    expect((await rootRows.allTextContents()).join('\n')).not.toContain('未分类')
    await page.screenshot({ path: path.join(evidenceDir, '02-iss028-root-category-filter-desktop.png'), fullPage: true })

    await rootFilter.selectOption(String(child.id))
    await expect(page).toHaveURL(new RegExp(`[?&]category=${child.id}(?:&|$)`))
    const childRows = page.locator('.product-list-table tbody tr')
    await expect(childRows).toHaveCount(2)
    await expect(childRows.filter({ hasText: editableMobile.name })).toBeVisible()
    await expect(childRows.filter({ hasText: childProduct.name })).toBeVisible()
    await expect(childRows.filter({ hasText: editableDesktop.name })).toHaveCount(0)
    await page.screenshot({ path: path.join(evidenceDir, '03-iss028-child-category-filter-desktop.png'), fullPage: true })

    const mobileAssignment = await assignRootCategory(page, editableMobile, root.id, rootName, 390, '04-iss028-root-category-assignment-390.png')
    layoutResults.push({ scenario: 'root-category-assignment-390', ...mobileAssignment.layout })
    const mobileRootFilter = page.getByLabel('产品分类筛选')
    await mobileRootFilter.selectOption(String(root.id))
    await expect(page).toHaveURL(new RegExp(`[?&]category=${root.id}(?:&|$)`))
    const mobileRootRows = page.locator('.product-list-table tbody tr')
    await expect(mobileRootRows).toHaveCount(3)
    await expect(mobileRootRows.filter({ hasText: editableMobile.name })).toBeVisible()
    await page.screenshot({ path: path.join(evidenceDir, '05-iss028-root-category-filter-390.png'), fullPage: true })
    await mobileRootFilter.selectOption(String(child.id))
    await expect(page).toHaveURL(new RegExp(`[?&]category=${child.id}(?:&|$)`))
    const mobileChildRows = page.locator('.product-list-table tbody tr')
    await expect(mobileChildRows).toHaveCount(1)
    await expect(mobileChildRows.filter({ hasText: childProduct.name })).toBeVisible()
    await page.screenshot({ path: path.join(evidenceDir, '06-iss028-child-category-filter-390.png'), fullPage: true })
    layoutResults.push({ scenario: 'category-filters-390', ...(await page.evaluate(() => ({ viewport: innerWidth, page: document.documentElement.scrollWidth, body: document.body.scrollWidth }))) })

    await page.setViewportSize({ width: 1440, height: 960 })
    await page.goto('/categories')
    await expect(page.locator('.page-head h2')).toHaveText('产品分类')
    await selectCategoryNode(page, childName)
    const inheritedRow = page.locator('.attribute-table tbody tr').filter({ hasText: `电压${id}` })
    await expect(inheritedRow).toContainText(`继承：${rootName}`)
    const inheritedSwitches = inheritedRow.locator('input[type="checkbox"]')
    await expect(inheritedSwitches).toHaveCount(4)
    for (const checkbox of await inheritedSwitches.all()) await expect(checkbox).toBeDisabled()
    await page.screenshot({ path: path.join(evidenceDir, '07-iss028-inherited-attributes-1440.png'), fullPage: true })
    const desktopCategoryLayout = await measureCategoryLayout(page)
    layoutResults.push({ scenario: 'inherited-attributes-1440', ...desktopCategoryLayout })
    await page.setViewportSize({ width: 390, height: 844 })
    await expect(inheritedRow).toBeVisible()
    await expect(inheritedRow).toContainText(`继承：${rootName}`)
    const narrow = await measureCategoryLayout(page)
    await page.screenshot({ path: path.join(evidenceDir, '08-iss028-inherited-attributes-390.png'), fullPage: true })
    expect(narrow.page).toBeLessThanOrEqual(narrow.viewport)
    expect(narrow.body).toBeLessThanOrEqual(narrow.viewport)
    layoutResults.push({ scenario: 'inherited-attributes-390', ...narrow })

    saveJson('iss028-http-results.json', httpResults)
    saveJson('iss028-browser-layout.json', { viewports: [1440, 390], measurements: layoutResults, narrowSidebarDisposition: 'Observed and retained; no global layout changes in this verification.' })
  })

  test('ISS-035 模板变更不改写已发布 SKU、报价和订单快照', async ({ page }) => {
    const id = stamp()
    const rootName = `验收${id}模板根分类`
    const childName = `验收${id}模板子分类`
    const root = await api(page, 'post', '/categories/', { name: rootName, description: '合成模板快照验证' }, 201)
    const child = await api(page, 'post', '/categories/', { name: childName, parent: root.id, description: '合成模板快照验证' }, 201)
    const attribute = await api(page, 'post', '/category-attributes/', {
      category: root.id, name: `电压${id}`, key: `voltage_${id.toLowerCase()}`, default_value: '24', unit: 'V', include_in_sku: true,
    }, 201)
    const product = await api(page, 'post', '/products/', {
      name: `验收${id}已发布 SKU 产品`, name_en: 'Synthetic published SKU verification product',
      sales_model_prefix: `P${id}`, category: child.id, status: 'active', description: 'Synthetic UAT data only',
    }, 201)
    const sku = await api(page, 'post', '/skus/', {
      product: product.id, specification: '24V', parameter_values: { [attribute.key]: '24' },
      sales_model: `M${id}`, unit: 'pcs', description_cn: `验收${id}原始描述`, description_en: 'Synthetic original description',
    }, 201)
    const customer = await api(page, 'post', '/customers/', {
      name: `验收${id}合成客户`, country: 'US', address: 'Synthetic test address',
      contacts: [{ name: `验收${id}合成联系人`, email: `uat-${id.toLowerCase()}@example.com`, is_primary: true }],
    }, 201)
    const quote = await api(page, 'post', '/quotes/', {
      customer: customer.id, quote_date: '2026-10-28', currency: 'USD',
      items: [{ sku: sku.id, quantity: '1', unit_price: '10', description: 'Synthetic quote snapshot' }],
    }, 201)
    const sentQuote = await api(page, 'post', `/quotes/${quote.id}/mark-sent/`, {}, 200)
    expect(sentQuote.status).toBe('sent')
    const orderDraft = await api(page, 'get', `/quotes/${quote.id}/order-draft/`)
    const draftOrder = await api(page, 'post', '/orders/', orderDraft, 201)
    expect(draftOrder.status).toBe('draft')
    const order = await api(page, 'post', `/orders/${draftOrder.id}/confirm/`, {}, 200)
    expect(order.status).toBe('confirmed')
    expect(order.quote).toBe(quote.id)
    const acceptedQuote = await api(page, 'get', `/quotes/${quote.id}/`)
    expect(acceptedQuote.status).toBe('accepted')

    const initialProduct = await api(page, 'get', `/products/${product.id}/`)
    const initialSku = await api(page, 'get', `/skus/${sku.id}/`)
    expect(initialProduct.sku_definitions).toBeTruthy()
    expect(initialSku.schema_version).toBeGreaterThan(0)
    const ids = { root_id: root.id, child_id: child.id, attribute_id: attribute.id, product_id: product.id, sku_id: sku.id, quote_id: quote.id, order_id: order.id }
    const before = inspectDatabase(ids)
    expect(before.plans.some(plan => plan.status === 'published')).toBe(true)
    expect(before.quote[0].status).toBe('accepted')
    expect(before.order[0].status).toBe('confirmed')

    console.log('ISS-035: created isolated published SKU and synthetic quote/order snapshots; navigating to category template.')
    await page.setViewportSize({ width: 1440, height: 960 })
    await page.goto('/categories')
    await expect(page.locator('.page-head h2')).toHaveText('产品分类')
    await selectCategoryNode(page, rootName)
    console.log('ISS-035: selected the synthetic root category in the browser.')
    const templateRow = page.locator('.attribute-table tbody tr').filter({ hasText: `电压${id}` })
    await expect(templateRow).toBeVisible()
    const uppercaseRule = templateRow.locator('input[type="checkbox"]').nth(2)
    await expect(uppercaseRule).not.toBeChecked()
    await expect(uppercaseRule).toBeEnabled()
    await templateRow.locator('.rule-switch').nth(2).click()
    await expect(uppercaseRule).toBeChecked()
    console.log('ISS-035: changed the category template through the browser.')
    await page.screenshot({ path: path.join(evidenceDir, '09-iss035-category-template-changed-1440.png'), fullPage: true })
    await page.reload()
    await selectCategoryNode(page, rootName)
    console.log('ISS-035: reopened and refreshed category template in the browser.')
    const reopenedRule = page.locator('.attribute-table tbody tr').filter({ hasText: `电压${id}` }).locator('input[type="checkbox"]').nth(2)
    await expect(reopenedRule).toBeChecked()
    await expect(page.getByText('已发布的方案不会随模板自动变化；如需更新，请到产品页分析后发布。', { exact: false })).toBeVisible()
    await page.setViewportSize({ width: 390, height: 844 })
    await expect(reopenedRule).toBeVisible()
    await expect(reopenedRule).toBeChecked()
    const narrow = await measureCategoryLayout(page)
    await page.screenshot({ path: path.join(evidenceDir, '10-iss035-category-template-changed-390.png'), fullPage: true })
    expect(narrow.page).toBeLessThanOrEqual(narrow.viewport)
    expect(narrow.body).toBeLessThanOrEqual(narrow.viewport)
    layoutResults.push({ scenario: 'template-change-390', ...narrow })

    const changedProduct = await api(page, 'get', `/products/${product.id}/`)
    const changedSku = await api(page, 'get', `/skus/${sku.id}/`)
    expect(changedProduct.sku_definitions).toEqual(initialProduct.sku_definitions)
    expect(changedSku).toMatchObject({
      sku_code: initialSku.sku_code, sales_model: initialSku.sales_model, display_name_cn: initialSku.display_name_cn,
      specification: initialSku.specification, parameter_values: initialSku.parameter_values, schema_version: initialSku.schema_version,
    })
    console.log('ISS-035: API confirms the published plan and SKU identity are unchanged.')

    await page.setViewportSize({ width: 1440, height: 960 })
    await page.goto('/skus')
    const skuRow = page.locator('.sku-data-row').filter({ hasText: initialSku.sku_code })
    await expect(skuRow).toBeVisible()
    await skuRow.getByRole('button', { name: '编辑', exact: true }).click()
    console.log('ISS-035: opened the published SKU editor.')
    const skuEditor = page.getByRole('dialog', { name: '编辑 SKU' })
    await expect(skuEditor).toBeVisible()
    await skuEditor.locator('.description-fields textarea').first().fill(`验收${id}普通保存描述`)
    await page.screenshot({ path: path.join(evidenceDir, '11-iss035-ordinary-sku-save-1440.png'), fullPage: true })
    await skuEditor.locator('.modal-foot button').filter({ hasText: '保存' }).last().click()
    await expect(skuEditor).toBeHidden()
    const afterOrdinarySave = await api(page, 'get', `/skus/${sku.id}/`)
    expect(afterOrdinarySave).toMatchObject({
      sku_code: initialSku.sku_code, sales_model: initialSku.sales_model, display_name_cn: initialSku.display_name_cn,
      specification: initialSku.specification, parameter_values: initialSku.parameter_values, schema_version: initialSku.schema_version,
    })
    expect(afterOrdinarySave.description_cn).toBe(`验收${id}普通保存描述`)
    const savedSkuRow = page.locator('.sku-data-row').filter({ hasText: initialSku.sku_code })
    await savedSkuRow.getByRole('button', { name: '编辑', exact: true }).click()
    const reopenedSkuEditor = page.getByRole('dialog', { name: '编辑 SKU' })
    await expect(reopenedSkuEditor.locator('.description-fields textarea').first()).toHaveValue(`验收${id}普通保存描述`)
    await expect(reopenedSkuEditor.locator('.sales-model-field input')).toHaveValue(initialSku.sales_model)
    await page.screenshot({ path: path.join(evidenceDir, '12-iss035-reopened-sku-1440.png'), fullPage: true })
    await reopenedSkuEditor.getByRole('button', { name: '关闭 SKU 窗口' }).click()
    await expect(reopenedSkuEditor).toBeHidden()

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/skus')
    const mobileSkuRow = page.locator('.sku-data-row').filter({ hasText: initialSku.sku_code })
    await expect(mobileSkuRow).toBeVisible()
    await mobileSkuRow.getByRole('button', { name: '编辑', exact: true }).click()
    const mobileSkuEditor = page.getByRole('dialog', { name: '编辑 SKU' })
    await expect(mobileSkuEditor).toBeVisible()
    await expect(mobileSkuEditor.locator('.description-fields textarea').first()).toHaveValue(`验收${id}普通保存描述`)
    await expect(mobileSkuEditor.locator('.sales-model-field input')).toHaveValue(initialSku.sales_model)
    await mobileSkuEditor.locator('.description-fields textarea').first().fill(`验收${id}窄屏保存描述`)
    await page.screenshot({ path: path.join(evidenceDir, '13-iss035-ordinary-sku-save-390.png'), fullPage: true })
    await mobileSkuEditor.locator('.modal-foot button').filter({ hasText: '保存' }).last().click()
    await expect(mobileSkuEditor).toBeHidden()
    const afterMobileSave = await api(page, 'get', `/skus/${sku.id}/`)
    expect(afterMobileSave.description_cn).toBe(`验收${id}窄屏保存描述`)
    expect(afterMobileSave).toMatchObject({
      sku_code: initialSku.sku_code, sales_model: initialSku.sales_model, display_name_cn: initialSku.display_name_cn,
      specification: initialSku.specification, parameter_values: initialSku.parameter_values, schema_version: initialSku.schema_version,
    })
    await mobileSkuRow.getByRole('button', { name: '编辑', exact: true }).click()
    const reopenedMobileSkuEditor = page.getByRole('dialog', { name: '编辑 SKU' })
    await expect(reopenedMobileSkuEditor.locator('.description-fields textarea').first()).toHaveValue(`验收${id}窄屏保存描述`)
    await expect(reopenedMobileSkuEditor.locator('.sales-model-field input')).toHaveValue(initialSku.sales_model)
    await page.screenshot({ path: path.join(evidenceDir, '14-iss035-reopened-sku-390.png'), fullPage: true })
    await reopenedMobileSkuEditor.getByRole('button', { name: '关闭 SKU 窗口' }).click()
    await expect(reopenedMobileSkuEditor).toBeHidden()

    const newProduct = await api(page, 'post', '/products/', {
      name: `验收${id}模板变更后新产品`, name_en: 'Synthetic new product after template update',
      sales_model_prefix: `N${id}`, category: child.id, status: 'active', description: 'Synthetic UAT data only',
    }, 201)
    const newSku = await api(page, 'post', '/skus/', {
      product: newProduct.id, specification: '24V', parameter_values: { [attribute.key]: '24' },
      sales_model: `N${id}-24`, unit: 'pcs', description_cn: `验收${id}新模板 SKU`, description_en: 'Synthetic new schema SKU',
    }, 201)
    const newProductRead = await api(page, 'get', `/products/${newProduct.id}/`)
    expect(newProductRead.sku_definitions).toBeTruthy()
    expect(newProductRead.sku_definitions).not.toEqual(initialProduct.sku_definitions)
    expect(newProductRead.sku_definitions.find(definition => definition.key === attribute.key)?.uppercase).toBe(true)

    const finalIds = { ...ids, new_product_id: newProduct.id, new_sku_id: newSku.id }
    const after = inspectDatabase(finalIds)
    expect(Boolean(before.attributes.find(row => row.id === attribute.id)?.uppercase)).toBe(false)
    expect(Boolean(after.attributes.find(row => row.id === attribute.id)?.uppercase)).toBe(true)
    expect(after.sku[0]).toMatchObject({
      sku: before.sku[0].sku, sales_model: before.sku[0].sales_model, display_name_cn: before.sku[0].display_name_cn,
      specification: before.sku[0].specification, parameter_values: before.sku[0].parameter_values, schema_version: before.sku[0].schema_version,
    })
    expect(after.sku[0].description_cn).toBe(`验收${id}窄屏保存描述`)
    expect(after.plans[0].definitions).toEqual(before.plans[0].definitions)
    expect(after.quote).toEqual(before.quote)
    expect(after.order).toEqual(before.order)
    expect(after.quote_items).toEqual(before.quote_items)
    expect(after.order_items).toEqual(before.order_items)
    expect(after.new_product[0].category_id).toBe(child.id)
    expect(after.new_plans[0].definitions).not.toEqual(before.plans[0].definitions)
    expect(after.quote_items[0]).toMatchObject({
      sku_code_snapshot: before.sku[0].sku,
      sales_model_snapshot: before.sku[0].sales_model,
      unit_snapshot: 'pcs',
    })
    expect(after.order_items[0]).toMatchObject({
      sku_code_snapshot: before.sku[0].sku,
      sales_model_snapshot: before.sku[0].sales_model,
      unit_snapshot: 'pcs',
    })
    saveJson('iss035-api-and-db-snapshots.json', { ids: finalIds, before, after, http: httpResults })
    saveJson('iss035-browser-layout.json', { viewports: [1440, 390], measurements: layoutResults, narrowSidebarDisposition: 'Observed and retained; no global layout changes in this verification.' })
  })
})
