import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('S5 order status filtering and workbench recovery', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Run S5 in its dedicated authenticated isolation profile.')
  test.setTimeout(900000)
  const repository = fileURLToPath(new URL('../../', import.meta.url))
  const output = path.join(repository, 'docs/uat-evidence/sales-state-closeout-05')
  const root = process.env.ISOLATED_TEST_ROOT
  if (!root || process.env.ISOLATED_CODEX_TEST_SUPERADMIN !== '1') {
    throw new Error('Use the isolated runner with the authenticated codex fixture.')
  }
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repository, encoding: 'utf8' }).trim()
  const { orders, identifiers, quote, previousQuote, confirmOrders } = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.join(output, 'seed.py')], {
    cwd: path.join(repository, 'backend'), encoding: 'utf8',
  }))
  const screenshots = path.join(output, 'screenshots')
  await mkdir(screenshots, { recursive: true })
  const context = await chromium.launchPersistentContext(path.join(root, 's5-chrome'), { channel: 'chrome' })
  const results = []
  let browser
  let failure
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    const settings = context.pages()[0]
    const page = await context.newPage()
    page.setDefaultTimeout(20000)
    const session = await page.request.get(new URL('/api/session/current-operator/', baseURL).href)
    expect(await session.json()).toMatchObject({ name: 'codex', authenticated: true })
    const cdp = await context.newCDPSession(page)
    browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    await settings.goto('chrome://settings/appearance', { waitUntil: 'commit', timeout: 90000 })
    const zoomControl = settings.locator('settings-appearance-page select').filter({
      has: settings.locator('option[value="1.25"]'),
    })
    const filter = page.getByLabel('按订单状态筛选')
    const pane = page.locator('.workspace-pane:not([aria-hidden=true])')
    const rows = pane.locator('.order-list-table tbody tr')
    let matrixIndex = 0
    for (const zoom of [1, 1.25]) {
      await settings.bringToFront()
      await zoomControl.selectOption(String(zoom), { timeout: 90000 })
      await page.bringToFront()
      for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
        await page.setViewportSize({ width, height })
        await page.goto(new URL('/orders?search=S5-SO', baseURL).href)
        await expect(rows).toHaveCount(6)
        const metrics = await page.evaluate(() => ({ dpr: devicePixelRatio, cssWidth: innerWidth }))
        expect(metrics.dpr).toBe(zoom)
        expect(metrics.cssWidth).toBeCloseTo(width / zoom, 0)
        expect(await filter.locator('option').evaluateAll(options => options.map(option => option.value))).toEqual(['', ...Object.keys(orders)])
        for (const [status, number] of Object.entries(orders)) {
          await filter.selectOption(status)
          await expect(rows).toHaveCount(1)
          await expect(rows.first()).toContainText(number)
          const screenshot = `so-01-${status}-${width}-${zoom * 100}.png`
          await filter.scrollIntoViewIfNeeded()
          const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' })
          await writeFile(path.join(screenshots, screenshot), Buffer.from(data, 'base64'))
          results.push({ status, number, width, height, zoom, ...metrics, screenshot })
        }
        await filter.selectOption('draft')
        await expect(rows).toHaveCount(1)
        await expect(rows.first()).toContainText(orders.draft)
        await rows.first().click()
        const workbench = page.getByRole('dialog', { name: '订单工作台' })
        await expect(workbench).toContainText(orders.draft)
        await workbench.getByRole('button', { name: '关闭订单详情' }).click()
        await expect(filter).toHaveValue('draft')
        await expect(rows).toHaveCount(1)
        await pane.getByRole('button', { name: '重置', exact: true }).click()
        await expect(filter).toHaveValue('')
        await expect(rows).toHaveCount(12)
        await pane.getByPlaceholder('搜索订单号或客户').fill('S5-NO-MATCH')
        await expect(pane.getByText('没有符合当前条件的记录', { exact: true })).toBeVisible()
        const endpoint = url => url.pathname === `/api/orders/${identifiers.confirmed}/workbench/`
        await page.route(endpoint, route => route.request().method() === 'GET'
          ? route.fulfill({ status: 400, json: { detail: 'S5 合成工作台加载失败' } })
          : route.continue())
        try {
          await page.goto(new URL(`/orders?detail=${identifiers.confirmed}`, baseURL).href)
          await expect(workbench.locator('.detail-error')).toBeVisible()
          await expect(workbench).not.toContainText(orders.draft)
          const screenshot = `so-04-load-failed-${width}-${zoom * 100}.png`
          const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' })
          await writeFile(path.join(screenshots, screenshot), Buffer.from(data, 'base64'))
          results.push({ state: 'SO-04-load-failed', width, height, zoom, screenshot })
        } finally {
          await page.unroute(endpoint)
        }
        const loaded = page.waitForResponse(response => endpoint(new URL(response.url())) && response.ok())
        await workbench.getByRole('button', { name: '重试', exact: true }).click()
        await loaded
        await expect(workbench).toContainText(orders.confirmed)
        await expect(workbench).not.toContainText(orders.draft)
        await expect(workbench).toContainText('当前有效双方资料尚未记录')
        const activeOrder = page.getByRole('tab', { name: orders.confirmed, exact: true })
        await expect(activeOrder).toBeVisible()
        const orderList = page.getByRole('tab', { name: '订单管理', exact: true })
        if (!(await orderList.count())) {
          await workbench.getByRole('button', { name: '关闭订单详情' }).click()
        } else {
          await orderList.click()
        }
        const late = url => url.pathname === `/api/orders/${identifiers.production}/workbench/`
        let releaseLate
        const held = new Promise(resolve => { releaseLate = resolve })
        await page.route(late, async route => {
          await held
          await route.continue()
        })
        try {
          const started = page.waitForRequest(request => late(new URL(request.url())) && request.method() === 'GET')
          await rows.filter({ hasText: orders.production }).click()
          await started
          await page.getByRole('tab', { name: '订单管理', exact: true }).click()
          await rows.filter({ hasText: orders.draft }).click()
          await expect(workbench).toContainText(orders.draft)
          const lateResponse = page.waitForResponse(response => late(new URL(response.url())) && response.ok())
          releaseLate()
          await lateResponse
          await expect(workbench).toContainText(orders.draft)
          await expect(workbench).not.toContainText(orders.production)
          const screenshot = `so-04-late-response-${width}-${zoom * 100}.png`
          const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' })
          await writeFile(path.join(screenshots, screenshot), Buffer.from(data, 'base64'))
          results.push({ state: 'SO-04-late-response', width, height, zoom, screenshot })
        } finally {
          releaseLate()
          await page.unroute(late)
        }
        const quoteEndpoint = url => url.pathname === `/api/quotes/${quote}/workbench/`
        const quoteWorkbench = page.getByRole('dialog', { name: '报价工作台' })
        await page.goto(new URL(`/quotes?detail=${previousQuote}`, baseURL).href)
        await expect(quoteWorkbench).toContainText('S5-QUO-PREVIOUS')
        await expect(quoteWorkbench.getByText('S5 上一报价独立备注', { exact: true })).toBeVisible()
        await quoteWorkbench.getByRole('button', { name: '关闭报价详情' }).click()
        await page.route(quoteEndpoint, route => route.request().method() === 'GET'
          ? route.fulfill({ status: 400, json: { detail: 'S5 合成报价加载失败' } })
          : route.continue())
        try {
          await pane.locator('tbody tr').filter({ hasText: 'S5-QUO-DETAIL-LONG-REFERENCE' }).click()
          await expect(quoteWorkbench.locator('.detail-error')).toBeVisible()
          await expect(quoteWorkbench).not.toContainText('S5 上一报价独立备注')
        } finally {
          await page.unroute(quoteEndpoint)
        }
        const quoteLoaded = page.waitForResponse(response => quoteEndpoint(new URL(response.url())) && response.ok())
        await quoteWorkbench.getByRole('button', { name: '重试', exact: true }).click()
        await quoteLoaded
        await expect(quoteWorkbench).toContainText('S5-QUO-DETAIL-LONG-REFERENCE')
        await expect(quoteWorkbench).not.toContainText('S5 上一报价独立备注')
        await expect(quoteWorkbench.getByText('S5 合成报价条款备注', { exact: true })).toBeVisible()
        const screenshot = `quo-04-loaded-${width}-${zoom * 100}.png`
        const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' })
        await writeFile(path.join(screenshots, screenshot), Buffer.from(data, 'base64'))
        results.push({ state: 'QUO-04-recovered', width, height, zoom, screenshot })
        const confirmId = confirmOrders[matrixIndex++]
        await page.goto(new URL(`/orders?detail=${confirmId}`, baseURL).href)
        const confirmOrder = workbench.getByRole('button', { name: '确认订单', exact: true })
        const confirmAction = url => url.pathname === `/api/orders/${confirmId}/confirm/`
        const isConfirmation = request => confirmAction(new URL(request.url())) && request.method() === 'POST'
        let releaseConfirmation
        const pending = new Promise(resolve => { releaseConfirmation = resolve })
        let attempts = 0
        await page.route(confirmAction, async route => {
          if (!isConfirmation(route.request())) return route.continue()
          attempts++
          await pending
          await route.fulfill({ status: 400, json: { detail: 'S5 合成确认拒绝' } })
        })
        try {
          await confirmOrder.click()
          const requested = page.waitForRequest(isConfirmation)
          await page.getByTestId('dialog-confirm').click()
          await requested
          await expect(confirmOrder).toBeDisabled()
          expect(attempts).toBe(1)
          const rejected = page.waitForResponse(response => isConfirmation(response.request()) && response.status() === 400)
          releaseConfirmation()
          await rejected
          await expect(workbench).toContainText('S5 合成确认拒绝')
          const rejectedScreenshot = `so-03-rejected-${width}-${zoom * 100}.png`
          const rejectedImage = await cdp.send('Page.captureScreenshot', { format: 'png' })
          await writeFile(path.join(screenshots, rejectedScreenshot), Buffer.from(rejectedImage.data, 'base64'))
          results.push({ state: 'SO-03-rejected', width, height, zoom, screenshot: rejectedScreenshot, rejected: 400 })
          await expect(confirmOrder).toBeEnabled()
        } finally {
          releaseConfirmation()
          await page.unroute(confirmAction)
        }
        await confirmOrder.click()
        const confirmed = page.waitForResponse(response => isConfirmation(response.request()))
        await page.getByTestId('dialog-confirm').click()
        const response = await confirmed
        expect(response.status(), await response.text()).toBe(200)
        const stored = await page.request.get(new URL(`/api/orders/${confirmId}/`, baseURL).href)
        expect(await stored.json()).toMatchObject({ id: confirmId, status: 'confirmed' })
        await expect(confirmOrder).toHaveCount(0)
        const confirmedScreenshot = `so-03-confirmed-${width}-${zoom * 100}.png`
        const confirmedImage = await cdp.send('Page.captureScreenshot', { format: 'png' })
        await writeFile(path.join(screenshots, confirmedScreenshot), Buffer.from(confirmedImage.data, 'base64'))
        results.push({ state: 'SO-03-confirmed', width, height, zoom, screenshot: confirmedScreenshot, rejected: 400, confirmed: 200 })
      }
    }
  } catch (error) {
    failure = error.message
    throw error
  } finally {
    await writeFile(path.join(output, 'so-01.json'), JSON.stringify({ source, browser, results, failure }, null, 2) + '\n')
    await context.close()
  }
})
