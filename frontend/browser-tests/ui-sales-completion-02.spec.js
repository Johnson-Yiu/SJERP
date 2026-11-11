import { execFileSync } from 'node:child_process'
import { chromium, expect, test } from '@playwright/test'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

const viewports = [[1366, 768], [1440, 900], [390, 844]]

test('sales fixes on real Chrome with native page zoom', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const root = process.env.ISOLATED_TEST_ROOT
  const output = path.resolve(process.env.E1_R2_EVIDENCE_DIR)
  const extension = process.env.E1_R2_EXTRA || ''
  const widthFilter = process.env.E1_R2_WIDTH
  expect(['', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']).toContain(extension)
  if (widthFilter) expect(viewports.map(([width]) => String(width))).toContain(widthFilter)
  const core = !extension || extension === '1'
  await mkdir(output, { recursive: true })
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const seed = path.resolve('../docs/uat-evidence/ui-sales-completion-02/seed.py')
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], { encoding: 'utf8' }))
  const context = await chromium.launchPersistentContext(path.join(root, 'e1-r2-chrome'), {
    channel: 'chrome',
    viewport: { width: 1440, height: 900 },
  })
  context.setDefaultTimeout(75000)
  const results = []
  const failures = []
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    await context.addInitScript(({ origins }) => {
      const current = origins.find(entry => entry.origin === location.origin)
      for (const item of current?.localStorage || []) localStorage.setItem(item.name, item.value)
    }, { origins: auth.origins })
    const settings = context.pages()[0]
    await settings.goto('chrome://settings/appearance', { waitUntil: 'commit' })
    const zoomControl = settings.locator('settings-appearance-page select').filter({
      has: settings.locator('option[value="1.25"]'),
    })
    await expect(zoomControl).toBeVisible({ timeout: 150000 })
    const page = await context.newPage()
    const cdp = await context.newCDPSession(page)
    const browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    const save = () => writeFile(path.join(output, 'run.json'), JSON.stringify({ source, browser, results, failures }, null, 2))
    const go = route => page.goto(new URL(route, baseURL).href, { waitUntil: 'commit', timeout: 75000 })
    const button = name => page.getByRole('button', { name, exact: true }).first()

    const foregroundZoom = ['9', '10'].includes(extension)

    async function collect(state, check, focus) {
      for (const zoom of [1, 1.25]) {
        if (foregroundZoom) await settings.bringToFront()
        await zoomControl.selectOption(String(zoom))
        if (foregroundZoom) await page.bringToFront()
        for (const [width, height] of viewports) {
          if (widthFilter && String(width) !== widthFilter) continue
          const key = state + '-' + width + '-' + zoom * 100
          try {
            await page.setViewportSize({ width, height })
            await expect.poll(() => page.evaluate(() => devicePixelRatio), { timeout: 15000 }).toBeCloseTo(zoom, 2)
            if (width === 390) await expect.poll(() => page.locator('.sidebar').evaluate(el => el.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
            if (typeof focus === 'function') await focus()
            else if (focus) await focus.scrollIntoViewIfNeeded()
            const metrics = await page.evaluate(() => {
              const root = document.documentElement
              const initial = window.scrollX
              window.scrollTo(100000, window.scrollY)
              const horizontalMovement = window.scrollX - initial
              window.scrollTo(initial, window.scrollY)
              const outside = [...document.querySelectorAll('body *')].filter(el => {
                const rect = el.getBoundingClientRect()
                return rect.width && rect.right > innerWidth + 4
              }).sort((a,b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right).slice(0, 6)
                .map(el => ({ className: el.getAttribute('class'), right: el.getBoundingClientRect().right }))
              return { dpr: devicePixelRatio, clientWidth: root.clientWidth, scrollWidth: root.scrollWidth, horizontalMovement, outside }
            })
            const file = key + '.png'
            const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
            await writeFile(path.join(output, file), Buffer.from(data, 'base64'))
            const result = { key, width, height, zoom, file, ...metrics }
            results.push(result)
            await check(result)
          } catch (error) {
            failures.push({ key, error: String(error.message).slice(0, 900) })
          }
          await save()
        }
      }
      if (foregroundZoom) await settings.bringToFront()
      await zoomControl.selectOption('1')
      if (foregroundZoom) await page.bringToFront()
      await page.setViewportSize({ width: 1440, height: 900 })
    }

    const noPageOverflow = result => {
      expect(result.scrollWidth).toBeLessThanOrEqual(result.clientWidth + 1)
      expect(result.horizontalMovement).toBe(0)
    }
    async function scenario(key, run) {
      try { await run() }
      catch (error) { failures.push({ key, error: String(error.message).slice(0, 900) }); await save() }
    }

    if (core) await scenario('quote-editor', async () => {
      await go('/quotes')
      await button('新建报价').click()
      const editor = page.getByRole('form', { name: '报价编辑器' })
      await expect(editor).toBeVisible()
      await collect('quote-new', noPageOverflow)
      await editor.locator('.sku-picker-options label').filter({ hasText: 'SYNTH-SALES-SKU-001' }).getByRole('checkbox').check()
      await expect(editor.locator('.quote-line-row')).toHaveCount(1)
      await collect('quote-selected', async result => {
        noPageOverflow(result)
        const table = editor.locator('.quote-line-items')
        const local = await table.evaluate(el => {
          const start = el.scrollLeft
          el.scrollLeft = el.scrollWidth
          const metrics = { width: el.clientWidth, scrollWidth: el.scrollWidth, moved: el.scrollLeft - start }
          el.scrollLeft = start
          return metrics
        })
        result.lineTable = local
        if (result.clientWidth <= 760) expect(local.moved).toBeGreaterThan(0)
      })
    })

    if (extension === '1') await scenario('quote-editor-recovery', async () => {
      const editor = page.getByRole('form', { name: '报价编辑器' })
      await editor.getByRole('button', { name: '保存报价', exact: true }).click()
      const requiredCustomer = editor.getByText('请选择客户。', { exact: true })
      await expect(requiredCustomer).toBeVisible()
      await collect('quote-selected-validation', async result => {
        noPageOverflow(result)
        await expect(requiredCustomer).toBeVisible()
      })

      const availability = '**/api/quotes/availability-preview/'
      let abort
      const release = new Promise(resolve => { abort = resolve })
      await page.route(availability, async route => { await release; await route.abort('failed') })
      try {
        await button('刷新库存').click()
        const loading = editor.getByText('正在读取库存参考…', { exact: true })
        await expect(loading).toBeVisible()
        await collect('quote-stock-loading', async result => {
          noPageOverflow(result)
          await expect(loading).toBeVisible()
        })
      } finally { abort() }
      const failure = editor.getByText('库存参考暂时无法读取，可继续报价。', { exact: true })
      await expect(failure).toBeVisible()
      await page.unroute(availability)
      await collect('quote-stock-failed', async result => {
        noPageOverflow(result)
        await expect(failure).toBeVisible()
      })
      const recovered = page.waitForResponse(r => r.url().endsWith('/availability-preview/'))
      await button('刷新库存').click()
      expect((await recovered).status()).toBe(200)
      await expect(editor.getByText('库存可覆盖', { exact: true })).toBeVisible()

      await button('生成预计装箱方案').click()
      await editor.getByRole('button', { name: /补充默认包装/ }).click()
      const packaging = page.locator('.packaging-config-modal')
      await expect(packaging.getByRole('heading', { name: '补充 SKU 默认包装' })).toBeVisible()
      await collect('quote-packaging-child', async result => {
        noPageOverflow(result)
        await packaging.getByRole('button', { name: '取消' }).click({ trial: true })
      })
      await packaging.getByRole('button', { name: '取消' }).click()
      await expect(packaging).toHaveCount(0)
      await expect(editor.locator('.quote-line-row')).toHaveCount(1)
      await expect(editor.getByRole('button', { name: /补充默认包装/ })).toBeVisible()

      await editor.getByRole('button', { name: '取消', exact: true }).click()
      await collect('quote-unsaved-close', async result => {
        noPageOverflow(result)
        await expect(button('继续编辑')).toBeVisible()
        await expect(button('放弃修改')).toBeVisible()
      })
      await button('继续编辑').click()
      await expect(editor.locator('.quote-line-row')).toHaveCount(1)
      await editor.getByRole('button', { name: '取消', exact: true }).click()
      await button('放弃修改').click()
      await expect(editor).toHaveCount(0)
    })

    if (core) await scenario('quote-revision', async () => {
      await go('/quotes?detail=' + fixture.quote)
      await button('创建修订版').click()
      await expect(page.locator('.quote-line-row')).toHaveCount(4)
      await collect('quote-revision', noPageOverflow)
    })

    if (core) await scenario('quote-preview', async () => {
      await go('/quotes?detail=' + fixture.quote)
      await button('预览 PI').click()
      const modal = page.getByRole('dialog', { name: 'PI 预览' })
      const img = modal.frameLocator('iframe[title="已保存 PI"]').locator('tbody img').first()
      await expect(modal).toBeVisible()
      await collect('quote-pi', async result => {
        await expect.poll(() => img.evaluate(node => node.naturalWidth)).toBe(48)
        await expect(img).toBeVisible()
        result.snapshot = await img.evaluate(node => ({
          imageOrigin: new URL(node.currentSrc).origin,
          frameOrigin: new URL(node.ownerDocument.baseURI).origin,
          width: node.naturalWidth,
        }))
        expect(result.snapshot.imageOrigin).toBe(result.snapshot.frameOrigin)
        noPageOverflow(result)
      })
      await modal.getByRole('button', { name: '关闭预览' }).click()
      await expect(button('预览 PI')).toBeVisible()
    })

    if (core) await scenario('order-badge', async () => {
      await go('/orders?detail=' + fixture.order)
      const badge = page.locator('.detail-identity .detail-badge')
      await expect(badge).toBeVisible()
      await collect('order-badge', async result => {
        const lines = await badge.evaluate(el => {
          const range = document.createRange()
          range.selectNodeContents(el)
          return new Set([...range.getClientRects()].map(rect => rect.top)).size
        })
        result.badgeLines = lines
        expect(lines).toBe(1)
        noPageOverflow(result)
      })
    })

    if (extension === '2') await scenario('order-terminal-states', async () => {
      await go('/orders?detail=' + fixture.order)
      const workbench = page.getByRole('dialog', { name: '订单工作台' })
      await workbench.getByRole('button', { name: '取消订单', exact: true }).click()
      const cancellation = page.locator('.trade-shipment-dialog').filter({ has: page.getByRole('heading', { name: '取消订单' }) })
      const confirm = cancellation.getByRole('button', { name: '确认取消', exact: true })
      await expect(confirm).toBeDisabled()
      await collect('order-cancel-required', async result => {
        noPageOverflow(result)
        await expect(confirm).toBeDisabled()
        await expect(cancellation.getByRole('button', { name: '返回' })).toBeVisible()
      })
      await cancellation.getByRole('button', { name: '返回' }).click()
      await expect(workbench.getByRole('button', { name: '编辑草稿' })).toBeVisible()
      await workbench.getByRole('button', { name: '取消订单', exact: true }).click()
      const reason = 'SYNTH-SALES 验收取消'
      await cancellation.getByLabel('取消原因').fill(reason)
      const cancelled = page.waitForResponse(r => r.url().endsWith('/cancel/') && r.request().method() === 'POST')
      await confirm.click()
      expect((await cancelled).status()).toBe(200)
      await expect(cancellation).toHaveCount(0)
      await go('/orders?detail=' + fixture.order)
      await expect(workbench.locator('.detail-badge')).toContainText('已取消')
      await expect(workbench.getByText(reason, { exact: false }).first()).toBeVisible()
      await collect('order-cancelled-read-only', async result => {
        noPageOverflow(result)
        await expect(workbench.getByRole('button', { name: '编辑草稿' })).toHaveCount(0)
        await expect(workbench.getByRole('button', { name: '取消订单' })).toHaveCount(0)
      })

      await go('/orders?detail=' + fixture.completedOrder)
      await expect(workbench.locator('.detail-badge')).toContainText('已完成')
      await collect('order-completed-read-only', async result => {
        noPageOverflow(result)
        await expect(workbench.getByRole('button', { name: '编辑草稿' })).toHaveCount(0)
        await expect(workbench.getByRole('button', { name: '取消订单' })).toHaveCount(0)
        await expect(workbench.getByRole('button', { name: '完成履约' })).toHaveCount(0)
      })
    })

    if (extension === '3') await scenario('order-procurement-draft', async () => {
      await go('/orders?detail=' + fixture.procurementOrder)
      const workbench = page.getByRole('dialog', { name: '订单工作台' })
      await workbench.getByRole('button', { name: '采购与发货', exact: true }).click()
      await button('生成采购草稿').click()
      const drawer = page.getByRole('dialog', { name: '采购草稿预览' })
      await expect(drawer.getByRole('heading', { name: '合成采购来源 · CNY' })).toBeVisible()
      const create = drawer.getByRole('button', { name: '创建 采购草稿' })
      const quantity = drawer.getByRole('row').filter({ hasText: 'SYNTH-PROCUREMENT' }).getByRole('spinbutton').first()
      await quantity.fill('16')
      await expect(drawer.getByText('本次采购数量必须介于 0 与当前可生成数量之间。')).toBeVisible()
      await expect(create).toBeDisabled()
      await quantity.fill('15')
      await collect('order-procurement-draft-preview', async result => {
        noPageOverflow(result)
        await expect(create).toBeEnabled()
      })

      const created = page.waitForResponse(r => r.url().endsWith('/generate-purchase-drafts/') && r.request().method() === 'POST')
      await create.click()
      const response = await created
      expect(response.status()).toBe(201)
      const { created_count, purchase_orders } = await response.json()
      expect(created_count).toBe(1)
      const [draft] = purchase_orders
      await expect(drawer).toHaveCount(0)
      await expect(workbench.getByRole('link', { name: draft.purchase_no })).toBeVisible()
      const stored = await page.request.get(`/api/purchase-orders/${draft.id}/`)
      expect(stored.status()).toBe(200)
      const record = await stored.json()
      expect(record.status).toBe('draft')
      expect(record.order).toBe(fixture.procurementOrder)
      expect(Number(record.items[0].quantity)).toBe(15)
      await go('/orders?detail=' + fixture.procurementOrder)
      await workbench.getByRole('button', { name: '采购与发货', exact: true }).click()
      await collect('order-procurement-draft-reopened', async result => {
        noPageOverflow(result)
        await expect(workbench.getByRole('link', { name: draft.purchase_no })).toBeVisible()
        await expect(button('生成采购草稿')).toBeDisabled()
      })
      results.push({ key: 'procurement-created-http', status: 201, purchase: draft.purchase_no, draftQuantity: 15 })
      await save()
    })

    if (extension === '4') await scenario('quote-trade-unit-and-packaging', async () => {
      await go('/quotes?create=1&customer=' + fixture.customer)
      const editor = page.getByRole('form', { name: '报价编辑器' })
      await editor.locator('.sku-picker-options label').filter({ hasText: 'SYNTH-SALES-SKU-001' }).getByRole('checkbox').check()
      const tradeUnit = editor.getByLabel('交易单位与包装规格')
      await tradeUnit.selectOption(String(fixture.tradeUnit))
      await editor.getByLabel('数量', { exact: true }).fill('2')
      await expect(editor.getByText(/^2(?:\.0+)? 箱 = 10 pcs$/)).toBeVisible()
      await button('生成预计装箱方案').click()
      await editor.getByRole('button', { name: /补充默认包装/ }).click()
      const packaging = page.locator('.packaging-config-modal')
      await packaging.locator('select').selectOption(String(fixture.carton))
      await packaging.getByRole('spinbutton').nth(0).fill('5')
      await packaging.getByRole('spinbutton').nth(1).fill('0.5')
      const savedPackaging = page.waitForResponse(r => r.url().endsWith('/packaging/') && r.request().method() === 'PUT')
      await packaging.getByRole('button', { name: '保存默认包装' }).click()
      expect((await savedPackaging).status()).toBe(200)
      await expect(packaging).toHaveCount(0)
      await expect(editor.locator('.packing-table-wrap tbody tr')).toHaveCount(2)
      await editor.locator('.packing-summary').scrollIntoViewIfNeeded()
      await collect('quote-packaging-saved-return', async result => {
        noPageOverflow(result)
        await expect(editor.getByText(/^2(?:\.0+)? 箱 = 10 pcs$/)).toBeVisible()
        await expect(editor.locator('.packing-table-wrap tbody tr')).toHaveCount(2)
      })

      const created = page.waitForResponse(r => r.url().endsWith('/api/quotes/') && r.request().method() === 'POST')
      await editor.getByRole('button', { name: '保存报价', exact: true }).click()
      const response = await created
      const saved = await response.json()
      expect(response.status(), JSON.stringify(saved)).toBe(201)
      expect(Number(saved.items[0].trade_unit)).toBe(fixture.tradeUnit)
      await go('/quotes?edit=' + saved.id)
      await expect(tradeUnit).toHaveValue(String(fixture.tradeUnit))
      await expect.poll(() => editor.getByLabel('数量', { exact: true }).evaluate(input => Number(input.value))).toBe(2)
      await expect(editor.getByText(/^2(?:\.0+)? 箱 = 10 pcs$/)).toBeVisible()
      await button('生成预计装箱方案').click()
      await expect(editor.locator('.packing-table-wrap tbody tr')).toHaveCount(2)
      results.push({ key: 'quote-trade-unit-reopened-http', quoteStatus: 201, packagingStatus: 200, cartons: 2, baseQuantity: 10 })
      await save()
    })

    if (['5', '8'].includes(extension)) await scenario('trade-shipment-overage', async () => {
      const reason = extension === '8' ? 'customer_addon' : 'packing_variance'
      const orderRoute = '/orders?detail=' + fixture.order
      const orderAction = suffix => r => r.url().endsWith('/api/orders/' + fixture.order + '/' + suffix + '/') && r.request().method() === 'POST'
      await go(orderRoute)
      await button('确认订单').click()
      const confirmed = page.waitForResponse(orderAction('confirm'))
      await page.getByTestId('dialog-confirm').click()
      expect((await confirmed).status()).toBe(200)
      await go(orderRoute + '&tab=fulfillment')
      const orderLine = page.getByRole('row').filter({ hasText: 'SYNTH-SALES-SKU-001' })
      await orderLine.getByRole('button', { name: '确认发货', exact: true }).click()
      const shipment = page.getByRole('dialog', { name: '确认发货' })
      const line = shipment.locator('.shipment-batch-line').filter({ hasText: 'SYNTH-SALES-SKU-001' })
      await expect(shipment.getByText('已选 1 条明细', { exact: true })).toBeVisible()
      await line.getByLabel('交易单位与包装规格').selectOption(String(fixture.tradeUnit))
      await line.getByRole('spinbutton', { name: /^发货数量/ }).fill('3')
      await expect(line.getByText(/交易数量 3 箱，折合 15 pcs/)).toBeVisible()
      await line.getByLabel(/^超发原因/).selectOption(reason)
      await collect('trade-shipment-' + reason, async result => {
        noPageOverflow(result)
        await expect(line.getByLabel(/^超发原因/)).toHaveValue(reason)
      }, line.getByLabel(/^超发原因/))
      await shipment.getByRole('button', { name: '确认发货', exact: true }).click()
      await expect(page.getByText('确认批量超发', { exact: true })).toBeVisible()
      const shipped = page.waitForResponse(orderAction('ship'))
      await page.getByTestId('dialog-confirm').click()
      const response = await shipped
      expect(response.status(), await response.text()).toBe(201)
      const shipmentId = (await response.json()).id
      const stored = await page.request.get('/api/orders/' + fixture.order + '/fulfillment/')
      expect(stored.status()).toBe(200)
      const shipmentRecord = (await stored.json()).shipments.find(row => row.id === shipmentId)
      expect(shipmentRecord.has_overage).toBe(true)
      expect(shipmentRecord.items.reduce((sum, item) => sum + Number(item.quantity), 0)).toBe(15)
      expect(shipmentRecord.items.filter(item => item.is_overage).reduce((sum, item) => sum + Number(item.quantity), 0)).toBe(5)
      if (reason === 'customer_addon') {
        const payload = response.request().postDataJSON()
        expect(payload.items).toHaveLength(1)
        expect(payload.items[0].overage_reason).toBe('customer_addon')
        results.push({ key: 'customer-overage-http', status: 201, shipped: 15, overage: 5 })
        await save()
        return
      }
      await go(orderRoute + '&tab=packing')
      const card = page.locator('.actual-shipment-card').first()
      await card.getByRole('button', { name: '新增箱', exact: true }).click()
      const packing = page.getByRole('dialog', { name: /^新增实际装箱记录/ })
      await packing.getByLabel('SKU 1', { exact: true }).selectOption({ index: 1 })
      const quantity = packing.getByLabel('实际装箱数量 1')
      const packingRequest = r => /\/api\/shipments\/\d+\/packages\/$/.test(r.url()) && r.request().method() === 'POST'
      async function submitPacking(value, status) {
        await quantity.fill(value)
        const submitted = page.waitForResponse(packingRequest)
        await packing.getByRole('button', { name: '保存实际装箱' }).click()
        const reply = await submitted
        expect(reply.status(), await reply.text()).toBe(status)
      }
      await submitPacking('1', 400)
      await expect(packing.getByRole('alert')).toContainText('整数倍')
      await collect('packing-indivisible-unit', async result => {
        noPageOverflow(result)
        await expect(packing.getByRole('alert')).toContainText('整数倍')
      }, packing.getByRole('alert'))
      await submitPacking('100', 400)
      await expect(packing.getByRole('alert')).toContainText('累计装箱数量不能超过')
      await collect('packing-over-quantity', async result => {
        noPageOverflow(result)
        await expect(packing.getByRole('alert')).toContainText('累计装箱数量不能超过')
      }, packing.getByRole('alert'))
      await submitPacking('5', 201)
      await go(orderRoute + '&tab=packing')
      await expect(card.locator('.actual-carton-card')).toHaveCount(1)
      results.push({ key: 'trade-shipment-packing-http', shipment: 201, indivisible: 400, overpack: 400, retry: 201 })
      await save()
    })

    if (extension === '6') await scenario('customer-related-quote-child', async () => {
      await go('/customers?detail=' + fixture.customer)
      const detail = page.getByRole('dialog', { name: '客户详情' })
      const quoteTab = detail.locator('.detail-tabs').getByRole('button', { name: /报价/ })
      await quoteTab.click()
      const openQuote = detail.getByRole('button', { name: '新建报价', exact: true })
      await openQuote.click()
      const editor = page.getByRole('form', { name: '报价编辑器' })
      const customer = editor.locator('select[required]').first()
      await expect(customer).toHaveValue(String(fixture.customer))
      await expect(customer).toBeDisabled()
      await collect('customer-related-quote-inherited', async result => {
        noPageOverflow(result)
        await expect(customer).toHaveValue(String(fixture.customer))
      })
      await editor.getByRole('button', { name: '取消', exact: true }).click()
      await expect(editor).toHaveCount(0)
      await expect(quoteTab).toHaveClass(/active/)
      await openQuote.click()
      await editor.locator('.sku-picker-options label').filter({ hasText: 'SYNTH-SALES-SKU-001' }).getByRole('checkbox').check()
      const created = page.waitForResponse(r => r.url().endsWith('/api/quotes/') && r.request().method() === 'POST')
      await editor.getByRole('button', { name: '保存报价', exact: true }).click()
      const response = await created
      const data = await response.json()
      expect(response.status(), JSON.stringify(data)).toBe(201)
      expect(data.customer).toBe(fixture.customer)
      await expect(editor).toHaveCount(0)
      await expect(quoteTab).toHaveClass(/active/)
      await expect(detail.getByText(data.quote_no, { exact: true })).toBeVisible()
      await collect('customer-related-quote-return', async result => {
        noPageOverflow(result)
        await expect(detail.getByText(data.quote_no, { exact: true })).toBeVisible()
      }, detail.getByText(data.quote_no, { exact: true }))
      results.push({ key: 'customer-related-quote-http', status: 201, customer: fixture.customer, quote: data.quote_no })
      await save()
    })

    if (extension === '7') await scenario('customer-detail-editor-stacking', async () => {
      const customerList = url => url.pathname === '/api/customers/' && url.searchParams.has('search')
      const customerDetail = '/api/customers/' + fixture.customer + '/'
      let releaseList
      const listHeld = new Promise(resolve => { releaseList = resolve })
      await page.route(customerList, async route => { await listHeld; await route.abort('failed').catch(() => {}) })
      try {
        const listing = page.waitForRequest(request => customerList(new URL(request.url())))
        await go('/customers?detail=' + fixture.customer)
        await listing
        const detail = page.locator('.customer-detail-root')
        const editor = page.getByRole('dialog', { name: '编辑客户' })
        const loaded = page.waitForResponse(response => response.url().endsWith(customerDetail))
        await detail.getByRole('button', { name: '编辑客户', exact: true }).click()
        const response = await loaded
        expect(response.status()).toBe(200)
        const customer = await response.json()
        await expect(editor.getByRole('textbox').first()).toHaveValue(customer.name)
        await expect(detail.locator('..')).toHaveAttribute('inert', '')
        await collect('customer-detail-editor-held-list', async result => {
          noPageOverflow(result)
          await editor.getByRole('button', { name: '取消', exact: true }).click({ trial: true })
          await editor.getByRole('button', { name: '保存客户', exact: true }).click({ trial: true })
        })
        await page.setViewportSize({ width: 390, height: 844 })
        await editor.getByRole('button', { name: '取消', exact: true }).click()
        await expect(editor).toHaveCount(0)
        await expect(page.getByRole('dialog', { name: '客户详情' })).toBeVisible()
        await expect(detail.locator('..')).not.toHaveAttribute('inert', '')

        await page.setViewportSize({ width: 1440, height: 900 })
        let releaseDetail
        const detailHeld = new Promise(resolve => { releaseDetail = resolve })
        await page.route('**' + customerDetail, async route => { await detailHeld; await route.continue() })
        try {
          const requested = page.waitForRequest(request => request.url().endsWith(customerDetail))
          await detail.getByRole('button', { name: '编辑客户', exact: true }).click()
          await requested
          await detail.getByRole('button', { name: '关闭详情', exact: true }).click()
          await expect(detail).toHaveCount(0)
          const late = page.waitForResponse(reply => reply.url().endsWith(customerDetail))
          releaseDetail()
          const lateResponse = await late
          expect(lateResponse.status()).toBe(200)
          await lateResponse.finished()
          await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
          await expect(editor).toHaveCount(0)
        } finally {
          releaseDetail()
          await page.unroute('**' + customerDetail)
        }
        results.push({ key: 'customer-detail-edit-held-list-http', status: 200, staleResponseIgnored: true })
        await save()
      } finally {
        releaseList()
        await page.unroute(customerList)
      }
    })

    if (extension === '9') await scenario('customer-country-selector-recovery', async () => {
      const endpoint = url => url.pathname === '/api/customers/country-catalog/'
      let release
      const held = new Promise(resolve => { release = resolve })
      await page.route(endpoint, async route => { await held; await route.abort('failed') })
      const requested = page.waitForRequest(r => endpoint(new URL(r.url())))
      const failed = page.waitForEvent('requestfailed', r => endpoint(new URL(r.url())))
      const editor = page.getByRole('dialog', { name: '新建客户' })
      try {
        await go('/customers')
        await button('新建客户').click()
        await requested
        await expect(editor).toHaveCount(0)
        await collect('customer-country-loading', async result => {
          noPageOverflow(result)
          await expect(editor).toHaveCount(0)
        })
      } finally {
        release()
      }
      await failed
      const country = editor.getByLabel('国家/地区', { exact: true })
      const alert = editor.getByRole('alert').filter({ hasText: '国家/地区资料加载失败' })
      await expect(country).toBeDisabled({ timeout: 20000 })
      await page.unroute(endpoint)
      await collect('customer-country-load-error', async result => {
        noPageOverflow(result)
        await expect(alert).toBeVisible()
      }, alert)
      const retry = page.waitForResponse(r => r.url().includes('/customers/country-catalog/'))
      await alert.getByRole('button', { name: '重新加载', exact: true }).click()
      expect((await retry).status()).toBe(200)
      await expect(country).toBeEnabled()
      await country.fill('E1-NO-MATCH-COUNTRY')
      const noMatch = editor.getByText('暂无匹配选项', { exact: true })
      await collect('customer-country-no-match', async result => {
        noPageOverflow(result)
        await expect(noMatch).toBeVisible()
      }, async () => {
        await country.fill('E1-NO-MATCH-COUNTRY')
        await noMatch.scrollIntoViewIfNeeded()
      })
      await country.fill('Germany')
      await editor.locator('.combo-menu button').filter({ hasText: /Germany/ }).first().click()
      await expect(country).toHaveValue(/Germany/)
      await editor.locator('.field').filter({ hasText: '客户名称' }).locator('input').first().fill('SYNTH-SALES-CUSTOMER-COUNTRY')
      await editor.locator('.contact-create-card .contact-fields input').first().fill('合成国家验收联系人')
      const saved = page.waitForResponse(r => r.url().endsWith('/api/customers/') && r.request().method() === 'POST')
      await editor.getByRole('button', { name: '保存客户', exact: true }).click()
      const response = await saved
      const customer = await response.json()
      expect(response.status(), JSON.stringify(customer)).toBe(201)
      expect(customer.country).toBe('DE')
      const readback = await page.request.get('/api/customers/' + customer.id + '/')
      expect((await readback.json()).country).toBe('DE')
      results.push({ key: 'customer-country-selector-http', retry: 200, create: 201, country: customer.country })
      await save()
    })

    if (extension === '10') await scenario('follow-up-contact-selector', async () => {
      await go('/follow-ups?search=SYNTH-SALES')
      const row = page.getByRole('row').filter({ hasText: 'SYNTH-SALES 附件与重开' })
      await row.getByRole('button', { name: '编辑跟进记录' }).click()
      const editor = page.getByRole('dialog', { name: '编辑跟进记录' })
      const customer = editor.getByLabel('客户', { exact: true })
      const contact = editor.getByLabel('联系人', { exact: true })
      await expect(customer).toHaveValue(String(fixture.customer))
      await contact.selectOption(String(fixture.contact))
      await customer.selectOption(String(fixture.emptyCustomer))
      await expect(contact).toHaveValue('')
      await expect(contact.locator('option')).toHaveCount(1)
      await collect('follow-up-contact-empty', async result => {
        noPageOverflow(result)
        await expect(contact.locator('option')).toHaveCount(1)
      }, contact)
      await customer.selectOption(String(fixture.customer))
      await contact.selectOption(String(fixture.contact))
      await collect('follow-up-contact-selected', async result => {
        noPageOverflow(result)
        await expect(contact).toHaveValue(String(fixture.contact))
      }, contact)
      const saved = page.waitForResponse(r => r.url().endsWith('/api/follow-ups/' + fixture.followUp + '/') && r.request().method() === 'PUT')
      await editor.getByRole('button', { name: '保存跟进', exact: true }).click()
      const response = await saved
      expect(response.status(), await response.text()).toBe(200)
      await go('/follow-ups?search=SYNTH-SALES')
      await row.getByRole('button', { name: '编辑跟进记录' }).click()
      await expect(contact).toHaveValue(String(fixture.contact))
      await editor.getByRole('button', { name: '取消', exact: true }).click()
      await go('/follow-ups?detail=' + fixture.followUp)
      const parent = page.getByRole('dialog', { name: '跟进详情' })
      await parent.getByRole('button', { name: /合成销售联系人/ }).click()
      const nested = page.getByRole('dialog', { name: '联系人详情' })
      const back = nested.getByRole('button', { name: /^返回/ })
      await collect('follow-up-related-contact-child', async result => {
        noPageOverflow(result)
        await expect(nested).toContainText('合成销售联系人')
      }, back)
      await back.click()
      await expect(parent.getByRole('button', { name: /合成销售联系人/ })).toBeVisible()
      results.push({ key: 'follow-up-contact-selector-http', update: 200, contact: fixture.contact, nestedReturn: true })
      await save()
    })

    if (core) await scenario('follow-up-attachment-retry', async () => {
      await go('/follow-ups?search=SYNTH-SALES')
      const row = page.getByRole('row').filter({ hasText: 'SYNTH-SALES 附件与重开' })
      await row.getByRole('button', { name: '编辑跟进记录' }).click()
      const dialog = page.getByRole('dialog', { name: '编辑跟进记录' })
      const bytes = Buffer.from('E1-R2 synthetic evidence')
      await dialog.locator('input[type=file]').setInputFiles({ name: 'e1-r2-retry.txt', mimeType: 'text/plain', buffer: bytes })
      const pattern = '**/api/follow-ups/' + fixture.followUp + '/attachments/'
      await page.route(pattern, route => route.request().method() === 'POST' ? route.abort('failed') : route.continue())
      try {
        await button('保存跟进').click()
        const error = dialog.getByText(/附件上传失败/).first()
        await expect(error).toBeVisible()
        await collect('follow-up-upload-error', async result => {
          noPageOverflow(result)
          await expect(error).toHaveText(/跟进记录已保存，附件上传失败/)
          await expect(button('取消')).toBeEnabled()
          await button('取消').click({ trial: true, timeout: 5000 })
          await button('保存跟进').click({ trial: true, timeout: 5000 })
          await expect(button('保存跟进')).toBeEnabled()
          expect(await dialog.locator('.toast').count()).toBe(0)
          expect(await page.locator('.toast.error').count()).toBe(0)
        })
      } finally { await page.unroute(pattern) }
      const upload = page.waitForResponse(r => r.url().endsWith('/attachments/') && r.request().method() === 'POST')
      await button('保存跟进').click()
      expect((await upload).status()).toBe(201)
      await expect(dialog).toHaveCount(0)
      await row.getByRole('button', { name: '编辑跟进记录' }).click()
      const attachment = dialog.locator('.follow-up-attachment-editor-item.saved')
      await expect(attachment).toHaveCount(1)
      const href = await attachment.getByRole('link', { name: '查看' }).getAttribute('href')
      const downloaded = await page.request.get(new URL(href, baseURL).href)
      expect(downloaded.status()).toBe(200)
      expect(await downloaded.body()).toEqual(bytes)
      results.push({ key: 'follow-up-reopened-http', status: 200, bytes: bytes.length, attachmentCount: 1 })
      await save()
    })

    expect(failures, JSON.stringify(failures, null, 2)).toEqual([])
    expect(results.some(result => result.file)).toBe(true)
  } finally {
    await context.close()
  }
})
