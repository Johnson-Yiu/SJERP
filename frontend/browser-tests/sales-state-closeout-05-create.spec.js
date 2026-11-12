import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('S5 creates and reopens an order draft', async ({ baseURL }) => {
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
  const { customer, sku } = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.join(output, 'seed.py')], {
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

    for (const zoom of [1, 1.25]) {
      await settings.bringToFront()
      await zoomControl.selectOption(String(zoom), { timeout: 90000 })
      await page.bringToFront()
      for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
        await page.setViewportSize({ width, height })
        await page.goto(new URL('/orders', baseURL).href, { waitUntil: 'commit', timeout: 90000 })
        const metrics = await page.evaluate(() => ({ dpr: devicePixelRatio, cssWidth: innerWidth }))
        expect(metrics.dpr).toBe(zoom)
        expect(metrics.cssWidth).toBeCloseTo(width / zoom, 0)
        const capture = async state => {
          const screenshot = `so-02-${state}-${width}-${zoom * 100}.png`
          const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' })
          await writeFile(path.join(screenshots, screenshot), Buffer.from(data, 'base64'))
          return screenshot
        }
        const isCreate = request => new URL(request.url()).pathname === '/api/orders/' && request.method() === 'POST'
        let creates = 0
        const countCreate = request => { if (isCreate(request)) creates++ }
        page.on('request', countCreate)
        await page.getByRole('button', { name: '新建订单', exact: true }).click()
        const editor = page.getByRole('dialog', { name: '新建销售订单草稿' })
        const save = editor.getByRole('button', { name: '保存销售订单草稿' })
        await save.click()
        await expect(page.getByText('请至少添加一条有效的 SKU 明细。', { exact: true })).toBeVisible()
        await editor.getByRole('combobox', { name: '单据币种' }).selectOption('CNY')
        await editor.getByRole('searchbox', { name: '搜索 SKU、型号或描述' }).fill('S5-SKU-001')
        await editor.getByRole('checkbox', { name: /S5-SKU-001/ }).check()
        const line = editor.locator('.line-row')
        const quantity = line.locator('input[min="0.01"]')
        const price = line.locator('input[type=number]').nth(1)

        await quantity.fill('0')
        await price.fill('37.25')
        await save.click()
        await expect(page.getByText('每条 SKU 明细的数量必须大于 0。', { exact: true })).toBeVisible()
        const invalid = await capture('invalid-quantity')
        expect(creates).toBe(0)
        await quantity.fill('3')
        const missing = page.waitForResponse(response => isCreate(response.request()) && response.status() === 400)
        await save.click()
        const missingCustomer = await (await missing).json()
        expect(missingCustomer).toHaveProperty('customer')
        await expect(editor).toBeVisible()
        await editor.locator('select[required]').selectOption(String(customer))
        await expect(line.getByRole('combobox', { name: '交易单位与包装规格' })).toContainText('pcs（基础单位）')
        await expect(editor.locator('.totals strong')).toContainText('111.75')
        const saved = page.waitForResponse(response => isCreate(response.request()) && response.status() === 201)
        await save.click()
        const created = await (await saved).json()
        expect(created).toMatchObject({ customer, currency: 'CNY', status: 'draft' })
        expect(Number(created.total_amount)).toBe(111.75)
        expect(created.items).toHaveLength(1)
        expect(created.items[0].sku).toBe(sku)
        expect(Number(created.items[0].quantity)).toBe(3)
        expect(Number(created.items[0].unit_price)).toBe(37.25)
        await expect(editor).toBeHidden()
        expect(creates).toBe(2)
        page.off('request', countCreate)
        const readback = page.waitForResponse(response => new URL(response.url()).pathname === `/api/orders/${created.id}/workbench/` && response.ok())
        await page.goto(new URL(`/orders?detail=${created.id}`, baseURL).href, { waitUntil: 'commit', timeout: 90000 })
        await readback
        const workbench = page.getByRole('dialog', { name: '订单工作台' })
        await expect(workbench).toContainText(created.order_no)
        await expect(workbench).toContainText('S5 合成商业展厅照明采购及设施维护服务有限公司')
        await expect(workbench).toContainText('111.75')
        const reopened = await capture('reopened')
        results.push({ width, height, zoom, ...metrics, invalid, reopened, missingCustomer, created })
      }
    }
  } catch (error) {
    failure = String(error.stack || error)
    throw error
  } finally {
    await writeFile(path.join(output, 'so-02.json'), JSON.stringify({ source, browser, results, failure }, null, 2) + '\n')
    await context.close()
  }
})
