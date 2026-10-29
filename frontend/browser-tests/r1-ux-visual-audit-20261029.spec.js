import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { expect, test } from '@playwright/test'

const widths = [1440, 1024, 390]
const pages = [
  { key: 'products', path: '/products', title: '产品管理' },
  { key: 'skus', path: '/skus', title: 'SKU 管理' },
  { key: 'customers', path: '/customers', title: '客户管理' },
  { key: 'quotes', path: '/quotes', title: '报价管理' },
  { key: 'orders', path: '/orders', title: '订单管理' },
  { key: 'purchase-orders', path: '/purchase-orders', title: '采购管理' },
  { key: 'inventory', path: '/inventory', title: '库存' },
  { key: 'inventory-movements', path: '/inventory-movements', title: '库存流水' },
  { key: 'finance', path: '/finance', title: '财务概览' },
  { key: 'transactions', path: '/transactions', title: '财务流水' },
  { key: 'reports', path: '/reports', title: '报表中心' },
  { key: 'receivables', path: '/receivables', title: '应收计划' },
  { key: 'payables', path: '/payables', title: '应付计划' },
]
const evidenceRoot = process.env.R1_UX_AUDIT_RUNNER_EVIDENCE_DIR
if (!evidenceRoot) throw new Error('R1_UX_AUDIT_RUNNER_EVIDENCE_DIR must point to this audit evidence directory.')
const screenshotRoot = path.join(evidenceRoot, 'screenshots')
const diagnostics = []

async function preparePage(browser, width) {
  const page = await browser.newPage({ viewport: { width, height: 1000 }, deviceScaleFactor: 1 })
  await page.route('https://fonts.googleapis.com/**', route => route.abort())
  await page.route('https://fonts.gstatic.com/**', route => route.abort())
  return page
}

async function inspect(page, key, width, state) {
  const layout = await page.evaluate(() => {
    const visible = element => {
      const rect = element.getBoundingClientRect()
      const style = getComputedStyle(element)
      return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none'
    }
    const overflow = [...document.querySelectorAll('body *')]
      .filter(element => visible(element) && element.scrollWidth > element.clientWidth + 2)
      .map(element => {
        const rect = element.getBoundingClientRect()
        return {
          tag: element.tagName.toLowerCase(),
          className: typeof element.className === 'string' ? element.className.slice(0, 100) : '',
          text: (element.innerText || '').trim().slice(0, 80),
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
          overflowX: getComputedStyle(element).overflowX,
          left: Math.round(rect.left),
          right: Math.round(rect.right),
        }
      }).slice(0, 20)
    return {
      innerWidth,
      innerHeight,
      documentClientWidth: document.documentElement.clientWidth,
      documentScrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      pageHorizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1,
      overflowElements: overflow,
      loadingStatus: [...document.querySelectorAll('[role="status"]')].filter(visible).map(element => (element.innerText || '').trim()).filter(Boolean),
      buttons: [...document.querySelectorAll('button')].filter(visible).map(button => ({
        text: (button.innerText || '').trim().slice(0, 80),
        ariaLabel: button.getAttribute('aria-label'),
        disabled: button.disabled,
        rect: (() => { const r = button.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)] })(),
      })),
      inputs: [...document.querySelectorAll('input,select,textarea')].filter(visible).map(input => ({
        tag: input.tagName.toLowerCase(),
        type: input.type || '',
        placeholder: input.getAttribute('placeholder'),
        ariaLabel: input.getAttribute('aria-label'),
        disabled: input.disabled,
      })),
    }
  })
  return { page: key, width, state, title: await page.title(), layout }
}

test.describe('R1-UX-VISUAL-AUDIT-01 real-browser evidence', () => {
  test.setTimeout(180_000)

  for (const width of widths) {
    test(`capture all requested business areas at ${width}px`, async ({ browser, baseURL }) => {
      await mkdir(screenshotRoot, { recursive: true })
      for (const spec of pages) {
        const page = await preparePage(browser, width)
        const consoleErrors = []
        const serverErrors = []
        page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()) })
        page.on('pageerror', error => consoleErrors.push(error.message))
        page.on('response', response => { if (response.status() >= 500) serverErrors.push(`${response.status()} ${response.url()}`) })
        let navigationError = ''
        try {
          await page.goto(new URL(spec.path, baseURL).href, { waitUntil: 'domcontentloaded' })
          await expect(page.locator('body')).toContainText(spec.title, { timeout: 15_000 })
          await page.waitForLoadState('networkidle', { timeout: 12_000 }).catch(() => {})
          await page.locator('.page-load-state-loading').waitFor({ state: 'hidden', timeout: 8_000 }).catch(() => {})
        } catch (error) {
          navigationError = error.message
        }
        const file = path.join(screenshotRoot, `${spec.key}-${width}.png`)
        await page.screenshot({ path: file, fullPage: false, animations: 'disabled' })
        diagnostics.push({
          ...(await inspect(page, spec.key, width, 'list')),
          screenshot: path.relative(evidenceRoot, file).replaceAll('\\', '/'),
          expectedTitle: spec.title,
          navigationError,
          consoleErrors,
          serverErrors,
        })
        if (spec.key === 'orders' && width === 390) {
          const scrollState = await page.locator('.table-wrap').first().evaluate(container => {
            const maxScroll = Math.max(0, container.scrollWidth - container.clientWidth)
            container.scrollLeft = maxScroll
            return { maxScroll, scrollLeft: container.scrollLeft, clientWidth: container.clientWidth, scrollWidth: container.scrollWidth }
          })
          expect(scrollState.maxScroll, 'the narrow order table should expose remaining columns through its own scroll container').toBeGreaterThan(0)
          const scrollFile = path.join(screenshotRoot, 'orders-table-horizontal-scroll-390.png')
          await page.screenshot({ path: scrollFile, fullPage: false, animations: 'disabled' })
          diagnostics.push({ ...(await inspect(page, 'orders-table-horizontal-scroll', 390, 'table-scroll-right')), ...scrollState, screenshot: path.relative(evidenceRoot, scrollFile).replaceAll('\\', '/') })
        }
        await page.close()
        expect(navigationError, `${spec.key} should render at ${width}px`).toBe('')
      }
    })
  }

  test('inspect order Packing List, page-two pagination, create dialogs, and actual export', async ({ browser, baseURL }) => {
    await mkdir(screenshotRoot, { recursive: true })
    const api = await browser.newPage({ baseURL })
    const ordersResponse = await api.request.get('/api/orders/?search=R1UXA-O001')
    expect(ordersResponse.ok()).toBeTruthy()
    const ordersPayload = await ordersResponse.json()
    const order = (Array.isArray(ordersPayload) ? ordersPayload : ordersPayload.results || []).find(row => row.order_no === 'R1UXA-O001')
    expect(order?.id).toBeTruthy()

    for (const width of widths) {
      const page = await preparePage(browser, width)
      const routeErrors = []
      page.on('pageerror', error => routeErrors.push(error.message))
      await page.goto(new URL(`/orders?detail=${order.id}&tab=packing`, baseURL).href, { waitUntil: 'domcontentloaded' })
      await expect(page.getByRole('dialog')).toBeVisible()
      const actualPacking = page.locator('.actual-packing-panel')
      await expect(actualPacking).toContainText('R1UXA-S001')
      await actualPacking.scrollIntoViewIfNeeded()
      const file = path.join(screenshotRoot, `packing-list-${width}.png`)
      await page.screenshot({ path: file, fullPage: false, animations: 'disabled' })
      diagnostics.push({ ...(await inspect(page, 'packing-list', width, 'actual-packing')), screenshot: path.relative(evidenceRoot, file).replaceAll('\\', '/') })
      if (width === 1440) {
        const [download] = await Promise.all([
          page.waitForEvent('download'),
          actualPacking.getByRole('button', { name: '导出 Packing List' }).click(),
        ])
        const exportPath = path.join(evidenceRoot, 'exports', download.suggestedFilename())
        await mkdir(path.dirname(exportPath), { recursive: true })
        await download.saveAs(exportPath)
        const downloadFailure = await download.failure()
        diagnostics.push({ page: 'packing-list-export', status: downloadFailure || 'downloaded', file: path.relative(evidenceRoot, exportPath).replaceAll('\\', '/') })
      }
      expect(routeErrors, `no uncaught browser errors for Packing List at ${width}px`).toEqual([])
      await page.close()
    }
    await api.close()

    const paginationPage = await preparePage(browser, 1440)
    await paginationPage.goto(new URL('/customers', baseURL).href, { waitUntil: 'domcontentloaded' })
    await expect(paginationPage.locator('body')).toContainText('R1UXA')
    const next = paginationPage.getByRole('button', { name: /下一页/ })
    if (await next.count()) {
      await next.first().click()
      await paginationPage.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => {})
      const file = path.join(screenshotRoot, 'customers-pagination-page-2-1440.png')
      await paginationPage.screenshot({ path: file, fullPage: false, animations: 'disabled' })
      diagnostics.push({ ...(await inspect(paginationPage, 'customers-pagination-page-2', 1440, 'page-2')), screenshot: path.relative(evidenceRoot, file).replaceAll('\\', '/') })
    } else {
      diagnostics.push({ page: 'customers-pagination', note: 'No visible next-page control found with 30 isolated synthetic customer rows.' })
    }
    await paginationPage.close()

    for (const [key, route, buttonName] of [
      ['product-form', '/products', /新建产品/],
      ['sku-form', '/skus', /新建 SKU|新建SKU/],
      ['customer-form', '/customers', /新建客户/],
      ['quote-form', '/quotes', /新建报价/],
      ['order-form', '/orders', /新建订单/],
      ['purchase-form', '/purchase-orders', /新建采购单/],
      ['transaction-form', '/transactions', /新增记账|新建财务流水|新增财务流水/],
    ]) {
      for (const width of widths) {
        const page = await preparePage(browser, width)
        await page.goto(new URL(route, baseURL).href, { waitUntil: 'domcontentloaded' })
        const button = page.getByRole('button', { name: buttonName }).first()
        await button.waitFor({ state: 'visible', timeout: 8_000 }).catch(() => {})
        if (await button.count()) {
          await button.click()
          const dialog = page.getByRole('dialog').first()
          await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => {})
          const dialogRoleVisible = await dialog.isVisible().catch(() => false)
          const file = path.join(screenshotRoot, `${key}-${width}.png`)
          await page.screenshot({ path: file, fullPage: false, animations: 'disabled' })
          diagnostics.push({ ...(await inspect(page, key, width, 'create-dialog')), dialogRoleVisible, url: page.url(), screenshot: path.relative(evidenceRoot, file).replaceAll('\\', '/') })
        } else {
          diagnostics.push({ page: key, width, note: 'Expected primary action was not found after waiting for visibility.' })
        }
        await page.close()
      }
    }

    const filterPage = await preparePage(browser, 390)
    await filterPage.goto(new URL('/customers', baseURL).href, { waitUntil: 'domcontentloaded' })
    const customerSearch = filterPage.getByRole('textbox', { name: '搜索客户' })
    await customerSearch.fill('R1UXA-C030')
    await expect(filterPage.locator('tbody tr')).toHaveCount(1, { timeout: 12_000 })
    await expect(filterPage.locator('tbody')).toContainText('R1UXA-C030')
    const filterFile = path.join(screenshotRoot, 'customers-search-filter-390.png')
    await filterPage.screenshot({ path: filterFile, fullPage: true, animations: 'disabled' })
    diagnostics.push({ ...(await inspect(filterPage, 'customers-search-filter', 390, 'synthetic-code-search')), resultRows: await filterPage.locator('tbody tr').count(), screenshot: path.relative(evidenceRoot, filterFile).replaceAll('\\', '/') })
    await filterPage.close()

    for (const width of [1440, 390]) {
      const editPage = await preparePage(browser, width)
      await editPage.goto(new URL('/products', baseURL).href, { waitUntil: 'domcontentloaded' })
      const editButton = editPage.getByRole('button', { name: '编辑产品' }).first()
      await editButton.waitFor({ state: 'visible', timeout: 10_000 })
      await editButton.click()
      await expect(editPage.getByRole('heading', { name: '编辑产品' })).toBeVisible()
      const editFile = path.join(screenshotRoot, `product-edit-${width}.png`)
      await editPage.screenshot({ path: editFile, fullPage: false, animations: 'disabled' })
      diagnostics.push({ ...(await inspect(editPage, 'product-edit', width, 'existing-synthetic-product-unsaved')), screenshot: path.relative(evidenceRoot, editFile).replaceAll('\\', '/') })
      await editPage.close()
    }

    const emptyPage = await preparePage(browser, 1440)
    await emptyPage.route('**/api/customers/**', async route => {
      if (route.request().method() === 'GET' && new URL(route.request().url()).pathname === '/api/customers/') {
        return route.fulfill({ status: 200, json: [] })
      }
      return route.continue()
    })
    await emptyPage.goto(new URL('/customers', baseURL).href, { waitUntil: 'domcontentloaded' })
    await expect(emptyPage.locator('body')).toContainText('暂无')
    const emptyFile = path.join(screenshotRoot, 'customers-empty-1440.png')
    await emptyPage.screenshot({ path: emptyFile, fullPage: false, animations: 'disabled' })
    diagnostics.push({ ...(await inspect(emptyPage, 'customers-empty', 1440, 'synthetic-empty-response')), screenshot: path.relative(evidenceRoot, emptyFile).replaceAll('\\', '/') })
    await emptyPage.close()

    const deniedPage = await preparePage(browser, 390)
    await deniedPage.route('**/api/session/current-operator/', route => route.fulfill({
      status: 200,
      json: { name: '仅用于拒绝状态视觉检查', rbac_enforcement: true, has_all_permissions: false, permissions: {} },
    }))
    await deniedPage.goto(new URL('/inventory', baseURL).href, { waitUntil: 'domcontentloaded' })
    await expect(deniedPage.locator('body')).toContainText('访问受限')
    const deniedFile = path.join(screenshotRoot, 'inventory-access-denied-390.png')
    await deniedPage.screenshot({ path: deniedFile, fullPage: false, animations: 'disabled' })
    diagnostics.push({ ...(await inspect(deniedPage, 'inventory-access-denied', 390, 'synthetic-denial-response')), screenshot: path.relative(evidenceRoot, deniedFile).replaceAll('\\', '/') })
    await deniedPage.close()

    const retryPage = await preparePage(browser, 1024)
    let forceProductsFailure = true
    await retryPage.route('**/api/products/**', async route => {
      const url = new URL(route.request().url())
      if (route.request().method() === 'GET' && url.pathname === '/api/products/' && forceProductsFailure) {
        return route.fulfill({ status: 503, json: { detail: '隔离验收模拟故障，请重试。' } })
      }
      return route.continue()
    })
    await retryPage.goto(new URL('/products', baseURL).href, { waitUntil: 'domcontentloaded' })
    const errorState = retryPage.getByRole('alert')
    await expect(errorState).toContainText('数据加载失败', { timeout: 20_000 })
    const failureFile = path.join(screenshotRoot, 'products-load-error-1024.png')
    await retryPage.screenshot({ path: failureFile, fullPage: false, animations: 'disabled' })
    diagnostics.push({ ...(await inspect(retryPage, 'products-load-error', 1024, 'synthetic-503-response')), screenshot: path.relative(evidenceRoot, failureFile).replaceAll('\\', '/') })
    forceProductsFailure = false
    await retryPage.getByRole('button', { name: '重新加载' }).click()
    const recoveredProductRow = retryPage.locator('.table-wrap tbody tr').first()
    await expect(recoveredProductRow).toBeVisible({ timeout: 20_000 })
    await expect(recoveredProductRow).toContainText('R1UXA-P01')
    const retryFile = path.join(screenshotRoot, 'products-retry-success-1024.png')
    await retryPage.screenshot({ path: retryFile, fullPage: false, animations: 'disabled' })
    diagnostics.push({ ...(await inspect(retryPage, 'products-retry-success', 1024, 'retry-after-synthetic-503')), screenshot: path.relative(evidenceRoot, retryFile).replaceAll('\\', '/') })
    await retryPage.close()

    await writeFile(path.join(evidenceRoot, 'browser-diagnostics.json'), JSON.stringify(diagnostics, null, 2), 'utf8')
    expect(diagnostics.some(row => row.page === 'packing-list-export' && row.status === 'downloaded')).toBeTruthy()
  })
})
