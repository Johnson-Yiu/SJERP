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
  const { orders, identifiers, quote } = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.join(output, 'seed.py')], {
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
        await expect(rows).toHaveCount(6)
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
        const quoteEndpoint = url => url.pathname === `/api/quotes/${quote}/workbench/`
        const quoteWorkbench = page.getByRole('dialog', { name: '报价工作台' })
        await page.route(quoteEndpoint, route => route.request().method() === 'GET'
          ? route.fulfill({ status: 400, json: { detail: 'S5 合成报价加载失败' } })
          : route.continue())
        try {
          await page.goto(new URL(`/quotes?detail=${quote}`, baseURL).href)
          await expect(quoteWorkbench.locator('.detail-error')).toBeVisible()
        } finally {
          await page.unroute(quoteEndpoint)
        }
        const quoteLoaded = page.waitForResponse(response => quoteEndpoint(new URL(response.url())) && response.ok())
        await quoteWorkbench.getByRole('button', { name: '重试', exact: true }).click()
        await quoteLoaded
        await expect(quoteWorkbench).toContainText('S5-QUO-DETAIL-LONG-REFERENCE')
        await expect(quoteWorkbench.getByText('S5 合成报价条款备注', { exact: true })).toBeVisible()
        const screenshot = `quo-04-loaded-${width}-${zoom * 100}.png`
        const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' })
        await writeFile(path.join(screenshots, screenshot), Buffer.from(data, 'base64'))
        results.push({ state: 'QUO-04-recovered', width, height, zoom, screenshot })
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
