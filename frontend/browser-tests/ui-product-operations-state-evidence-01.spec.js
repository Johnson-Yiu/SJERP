import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'
import { syntheticVoucherPdf } from './helpers/bank-voucher.js'

const repository = fileURLToPath(new URL('../../', import.meta.url))
const evidence = path.join(repository, 'docs/uat-evidence/ui-product-operations-state-evidence-01')
const routes = [
  ['/products', 'products', 'products', '新建产品'],
  ['/categories', 'categories', 'categories', '新建根分类'],
  ['/skus', 'skus', 'skus', '新建 SKU'],
  ['/product-parameters', 'parameters', 'product-parameters', '新建产品参数'],
  ['/suppliers', 'suppliers', 'suppliers', '新建供应商'],
  ['/purchase-orders', 'purchases', 'purchase-orders', '新建采购单'],
  ['/inventory', 'inventory', 'skus', ''],
  ['/inventory-movements', 'movements', 'inventory-movements', ''],
  ['/sku-packaging', 'packaging', 'packaging-templates', '新建模板'],
  ['/sku-trade-units', 'trade-units', 'sku-trade-units', ''],
  ['/product-certificates', 'certificates', 'product-certificates', '新建产品证书'],
  ['/hs-codes', 'hs-codes', 'hs-codes', '新建 HS 编码'],
]
const sizes = [[1366, 768], [1440, 900], [390, 844]]

test('product operations evidence with real Chrome and the isolated API', async ({ baseURL }) => {
  test.setTimeout(900000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repository, encoding: 'utf8' }).trim()
  const root = process.env.ISOLATED_TEST_ROOT
  const verify = process.env.PRODUCT_OPS_FOLLOWUP === 'verify'
  const followup = verify || process.env.PRODUCT_OPS_FOLLOWUP === '1'
  const indexName = verify ? 'browser-verification.json' : followup ? 'browser-followup.json' : 'browser-results.json'
  if (!root || process.env.ISOLATED_CODEX_TEST_SUPERADMIN !== '1') throw new Error('Run through the isolated codex profile.')
  const screenshots = path.join(evidence, 'screenshots')
  await mkdir(screenshots, { recursive: true })
  const context = await chromium.launchPersistentContext(path.join(root, 'product-operations-chrome'), {
    channel: 'chrome',
    viewport: { width: 1440, height: 900 },
  })
  const results = []
  const gaps = []
  let browser
  const saveIndex = () => writeFile(path.join(evidence, indexName), JSON.stringify({ source, browser, results, gaps }, null, 2) + '\n')
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    const settings = context.pages()[0]
    const page = await context.newPage()
    page.setDefaultTimeout(15000)
    page.setDefaultNavigationTimeout(45000)
    const cdp = await context.newCDPSession(page)
    browser = await cdp.send('Browser.getVersion')
    expect(browser.product).toMatch(/Chrome\//)
    const identity = await page.request.get(new URL('/api/session/current-operator/', baseURL).href)
    expect(await identity.json()).toMatchObject({ name: 'codex', authenticated: true, development_superadmin: false })
    let responses = []
    page.on('response', response => {
      const pathname = new URL(response.url()).pathname
      if (pathname.startsWith('/api/')) responses.push({ pathname, status: response.status(), method: response.request().method() })
    })
    async function capture(state, zoom, width, height, api = 'real') {
      const metrics = await page.evaluate(() => ({
        dpr: devicePixelRatio, cssWidth: innerWidth, cssHeight: innerHeight,
        documentWidth: document.documentElement.scrollWidth,
      }))
      expect(metrics.dpr).toBeCloseTo(zoom, 2)
      expect(metrics.cssWidth).toBeCloseTo(width / zoom, 0)
      if (metrics.cssWidth < 768) {
        await expect.poll(() => page.locator('.sidebar').evaluate(element => element.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
      }
      const screenshot = `${verify ? 'verification-' : followup ? 'followup-' : ''}${state}-${width}-${zoom * 100}.png`
      const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      await writeFile(path.join(screenshots, screenshot), Buffer.from(data, 'base64'))
      results.push({ state, screenshot, width, height, zoom, ...metrics, api, responses: [...responses] })
      await saveIndex()
    }
    async function open(route, endpoint, query = '') {
      responses = []
      const ready = page.waitForResponse(response => new URL(response.url()).pathname.startsWith(`/api/${endpoint}/`) && response.ok(), { timeout: 20000 })
      const settled = ready.catch(() => null)
      await page.goto(new URL(route + query, baseURL).href, { waitUntil: 'domcontentloaded' })
      const response = await settled
      if (!response) throw new Error(`No successful API response for ${endpoint}`)
      const pane = page.locator('.workspace-pane:not([aria-hidden=true])')
      await expect(pane).toBeVisible({ timeout: 8000 })
      await expect(pane.locator('.page-load-state-loading, .page-load-state-refreshing')).toHaveCount(0, { timeout: 8000 })
      if (route === '/purchase-orders') {
        await expect(pane.getByRole('button', { name: '新建采购单', exact: true })).toBeEnabled({ timeout: 8000 })
      }
      expect(new URL(page.url()).pathname).toBe(route)
    }
    async function attempt(state, action) {
      try { await action() } catch (error) { gaps.push({ state, message: error.message }) }
    }
    async function zoomTo(zoom) {
      if (settings.url() !== 'chrome://settings/appearance') {
        await settings.goto('chrome://settings/appearance', { waitUntil: 'domcontentloaded' })
      }
      await settings.locator('settings-appearance-page select').filter({
        has: settings.locator('option[value="1.25"]'),
      }).selectOption(String(zoom))
    }
    for (const [route, state, endpoint] of followup ? [] : routes) {
      await attempt(`${state}-empty`, async () => {
        await open(route, endpoint)
        await capture(`${state}-empty`, 1, 1440, 900)
      })
    }
    const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [
      path.join(evidence, 'seed.py'),
    ], { cwd: path.join(repository, 'backend'), encoding: 'utf8' }))
    await writeFile(path.join(evidence, 'fixture.json'), JSON.stringify(fixture, null, 2) + '\n')
    for (const zoom of verify ? [] : [1.25, 1]) {
      await zoomTo(zoom)
      for (const [route, state, endpoint, create] of routes) {
        if (followup && !(zoom === 1.25 && ['purchases', 'inventory', 'movements', 'packaging'].includes(state)) && !(zoom === 1 && state === 'packaging')) continue
        await attempt(`${state}-list-${zoom}`, async () => {
          await page.setViewportSize({ width: 1440, height: 900 })
          const query = state === 'trade-units' ? `?sku=${fixture.sku}` : ''
          await open(route, endpoint, query)
          for (const [width, height] of sizes) {
            await page.setViewportSize({ width, height })
            await capture(`${state}-list`, zoom, width, height)
          }
          if (!create) return
          await page.getByRole('button', { name: create, exact: true }).first().click()
          await page.getByRole('dialog').first().waitFor()
          for (const [width, height] of sizes) {
            await page.setViewportSize({ width, height })
            await capture(`${state}-create`, zoom, width, height)
          }
        })
      }
      for (const [route, state, endpoint, id] of [
          ['/products', 'product', 'products', fixture.product],
          ['/skus', 'sku', 'skus', fixture.sku],
          ['/suppliers', 'supplier', 'suppliers', fixture.supplier],
          ['/purchase-orders', 'purchase', 'purchase-orders', fixture.purchase],
          ['/inventory', 'stock', 'skus', fixture.sku],
      ]) {
        if (followup && !(zoom === 1 && state === 'supplier')) continue
        await attempt(`${state}-detail-${zoom}`, async () => {
          await open(route, endpoint, `?detail=${id}`)
          const detail = state === 'product' ? page.locator('.product-detail-modal') : page.getByRole('dialog').first()
          await detail.waitFor()
          await expect(detail).toContainText(/EVID-|合成长名称|合成供应商/, { timeout: 8000 })
          for (const [width, height] of sizes) {
            await page.setViewportSize({ width, height })
            await capture(`${state}-detail`, zoom, width, height)
          }
          if (state !== 'purchase') return
          await detail.getByText('采购明细', { exact: true }).first().click()
          await expect(detail.locator('tbody tr')).toHaveCount(4)
          for (const [width, height] of sizes) {
            await page.setViewportSize({ width, height })
            await capture('purchase-detail-items', zoom, width, height)
          }
        })
      }
    }
    await zoomTo(1.25)
    await page.setViewportSize({ width: 390, height: 844 })
    await attempt('product-search-no-match', async () => {
      await open('/products', 'products', '?search=EVID-NO-SUCH-PRODUCT')
      await expect(page.getByText('没有符合当前条件的记录', { exact: true })).toBeVisible()
      await capture('product-search-no-match', 1.25, 390, 844)
    })
    await attempt('product-load-failure', async () => {
      await open('/products', 'products')
      const endpoint = url => url.pathname === '/api/products/'
      await page.route(endpoint, route => route.fulfill({ status: 500, json: { detail: 'EVID controlled server failure' } }))
      try {
        responses = []
        const failed = page.waitForResponse(response => endpoint(new URL(response.url())) && response.status() === 500)
        await page.getByRole('button', { name: '刷新', exact: true }).click()
        await failed
        await expect(page.getByRole('button', { name: '重新加载', exact: true }).first()).toBeVisible()
        await capture('product-load-failure', 1.25, 390, 844, 'simulated products GET 500')
      } finally {
        await page.unroute(endpoint)
      }
    })
    await attempt('product-category-and-unsaved', async () => {
      await open('/products', 'products')
      await page.getByRole('button', { name: '新建产品', exact: true }).click()
      const form = page.getByRole('dialog', { name: '新建产品', exact: true })
      await form.locator('.category-select').first().click()
      await form.getByRole('button', { name: '合成灯具', exact: true }).click()
      await expect(form.getByRole('button', { name: '轨道灯与安装配件', exact: true })).toBeVisible()
      await capture('product-category-cascade', 1.25, 390, 844)
      await form.getByRole('button', { name: '轨道灯与安装配件', exact: true }).click()
      await form.getByRole('button', { name: '取消', exact: true }).click()
      await expect(page.getByText(/未保存/).last()).toBeVisible()
      await capture('product-unsaved', 1.25, 390, 844)
    })
    await attempt('purchase-edit-draft', async () => {
      await open('/purchase-orders', 'purchase-orders', `?detail=${fixture.purchase}`)
      await page.getByRole('button', { name: '编辑草稿', exact: true }).click()
      const form = page.getByRole('dialog', { name: '编辑采购草稿', exact: true })
      await expect(form.locator('.purchase-line')).toHaveCount(4)
      await capture('purchase-edit-draft', 1.25, 390, 844)
      await form.locator('.purchase-line').first().scrollIntoViewIfNeeded()
      await capture('purchase-edit-draft-line', 1.25, 390, 844)
    })
    await attempt('certificate-validate-and-upload', async () => {
      await open('/product-certificates', 'product-certificates')
      await page.getByRole('button', { name: '新建产品证书', exact: true }).click()
      const form = page.getByRole('dialog', { name: '新建产品证书', exact: true })
      await form.getByRole('combobox', { name: '所属产品', exact: true }).selectOption(String(fixture.product))
      const name = form.getByRole('textbox', { name: '证书名称', exact: true })
      const save = form.getByRole('button', { name: '保存证书', exact: true })
      const waitForSave = () => page.waitForResponse(response => response.url().endsWith('/api/product-certificates/') && response.request().method() === 'POST')
      const invalidName = 'EVID Synthetic certificate name '.repeat(7).trim()
      await name.fill(invalidName)
      const invalid = waitForSave()
      await save.click()
      expect((await invalid).status()).toBe(400)
      await expect(form.getByRole('alert')).toContainText('证书名称')
      await expect(name).toHaveValue(invalidName)
      await form.getByRole('alert').scrollIntoViewIfNeeded()
      await capture('certificate-field-error', 1.25, 390, 844)
      await name.fill('EVID 合成附件证书')
      const file = { name: 'EVID-synthetic-attachment.pdf', mimeType: 'application/pdf', buffer: syntheticVoucherPdf() }
      const input = form.locator('input[type=file]')
      await input.setInputFiles(file)
      await input.scrollIntoViewIfNeeded()
      await capture('certificate-upload-selected', 1.25, 390, 844)
      const uploaded = waitForSave()
      await save.click()
      const response = await uploaded
      expect(response.status()).toBe(201)
      const saved = await response.json()
      const fileResponse = await page.request.get(new URL(saved.file_url, baseURL).href)
      expect(fileResponse.status()).toBe(200)
      expect(await fileResponse.body()).toEqual(file.buffer)
      await expect(form).toHaveCount(0)
      const heading = page.getByRole('heading', { name: 'EVID 合成附件证书', exact: true })
      await expect(heading).toBeVisible()
      await heading.scrollIntoViewIfNeeded()
      await capture('certificate-upload-saved', 1.25, 390, 844)
    })
    await attempt('purchase-partial-receipt', async () => {
      const detailURL = `?detail=${fixture.purchase}`
      await open('/purchase-orders', 'purchase-orders', detailURL)
      const workbench = page.getByRole('dialog', { name: '采购工作台' })
      await workbench.getByRole('button', { name: /确认.*下单/ }).first().click()
      await capture('purchase-place-confirmation', 1.25, 390, 844)
      const place = page.waitForResponse(response => response.url().endsWith('/place/') && response.request().method() === 'POST')
      await page.getByTestId('dialog-confirm').click()
      expect((await place).ok()).toBeTruthy()
      await workbench.getByText('收货', { exact: true }).click()
      await workbench.locator('.receipt-heading button').first().click()
      const form = page.locator('form.receipt-dialog')
      await form.getByLabel(/本次合格入库数量/).fill('3')
      await form.getByLabel('指定入库仓库和批次').check()
      await form.getByLabel('仓库', { exact: true }).fill('合成收货仓')
      await form.getByLabel(/批次或货位/).fill('EVID-RECEIPT-A-01')
      await form.getByLabel(/已核对型号/).check()
      const submit = form.getByRole('button', { name: '确认入库', exact: true })
      await submit.scrollIntoViewIfNeeded()
      await capture('purchase-partial-receipt-form', 1.25, 390, 844)
      const received = page.waitForResponse(response => response.url().endsWith('/receive/') && response.request().method() === 'POST')
      await submit.click()
      expect((await received).ok()).toBeTruthy()
      await expect(form).toHaveCount(0)
      await expect(page.getByText(/验货入库已完成/).first()).toBeVisible()
      await capture('purchase-partial-receipt-saved', 1.25, 390, 844)
    })
    await attempt('purchase-cost-allocation', async () => {
      await open('/purchase-orders', 'purchase-orders', `?detail=${fixture.purchase}`)
      const workbench = page.getByRole('dialog', { name: '采购工作台' })
      await workbench.getByRole('button', { name: '分配采购成本 / 公共费用', exact: true }).click()
      const cost = page.locator('.cost-modal')
      const item = cost.locator('.cost-item').first()
      await expect(cost.locator('.cost-item')).toHaveCount(4)
      await capture('purchase-cost-overview', 1.25, 390, 844)
      const existingRows = item.locator('.cost-row')
      while (await existingRows.count()) {
        await existingRows.first().getByRole('button', { name: '删除', exact: true }).click()
      }
      for (const [order, quantity] of [['EVID-SO-001', '2'], ['EVID-SO-002', '3']]) {
        await item.getByRole('button', { name: '添加成本归属', exact: true }).click()
        const row = item.locator('.cost-row').last()
        await row.locator('select').nth(1).selectOption({ label: order })
        await row.locator('input[type=number]').fill(quantity)
      }
      await item.locator('.cost-row').last().scrollIntoViewIfNeeded()
      await capture('purchase-cost-multiple-orders', 1.25, 390, 844)
      const saved = page.waitForResponse(response => response.url().endsWith('/cost-allocation/') && response.request().method() === 'POST')
      await cost.getByRole('button', { name: '保存成本分配', exact: true }).click()
      const response = await saved
      if (!response.ok()) {
        await expect(cost.getByRole('alert')).toBeVisible()
        await cost.getByRole('alert').scrollIntoViewIfNeeded()
        await capture('purchase-cost-save-rejected', 1.25, 390, 844)
        throw new Error(`Cost allocation returned ${response.status()}: ${await response.text()}`)
      }
      await expect(cost.getByText('已保存的成本分摊结果')).toBeVisible()
      await cost.getByText('已保存的成本分摊结果').scrollIntoViewIfNeeded()
      await capture('purchase-cost-saved', 1.25, 390, 844)
    })
  } finally {
    await saveIndex()
    await context.close()
  }
})
