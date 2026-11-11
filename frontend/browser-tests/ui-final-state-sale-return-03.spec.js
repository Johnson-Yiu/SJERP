import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect as playwrightExpect, test } from '@playwright/test'

const expect = playwrightExpect.configure({ timeout: 30000 })

test('sales shipment and customer return are written and read back in the inventory ledger', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-sale-return')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-final-state-closeout-03/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, CLOSEOUT_SALE_RETURN: '1' },
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'sale-return-chrome'), {
    channel: 'chrome', viewport: { width: 390, height: 844 },
  })
  const states = []
  let browser
  let failure
  const save = () => writeFile(path.join(output, 'run.json'), JSON.stringify({ source, browser, states, failure }, null, 2) + '\n')
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    const settings = context.pages()[0]
    const page = await context.newPage()
    page.setDefaultTimeout(90000)
    const cdp = await context.newCDPSession(page)
    browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    await settings.goto('chrome://settings/appearance', { waitUntil: 'commit', timeout: 240000 })
    const zoomControl = settings.locator('settings-appearance-page select').filter({ has: settings.locator('option[value="1.25"]') })
    let zoom = 1.25
    await zoomControl.selectOption(String(zoom), { timeout: 180000 })
    const go = route => page.goto(new URL(route, baseURL).href, { waitUntil: 'commit', timeout: 240000 })
    const orderRoute = '/orders?detail=' + fixture.order
    const action = (suffix, method = 'POST') => page.waitForResponse(response =>
      new URL(response.url()).pathname.endsWith(suffix) && response.request().method() === method,
    { timeout: 90000 })
    await go(orderRoute)
    await page.getByRole('button', { name: '确认订单', exact: true }).click()
    const confirmed = action('/orders/' + fixture.order + '/confirm/')
    await page.getByTestId('dialog-confirm').click()
    expect((await confirmed).status()).toBe(200)
    await go(orderRoute + '&tab=fulfillment')
    await page.getByRole('row').filter({ hasText: fixture.sku_code })
      .getByRole('button', { name: '确认发货', exact: true }).click()
    const shipment = page.getByRole('dialog', { name: '确认发货' })
    const line = shipment.locator('.shipment-batch-line').filter({ hasText: fixture.sku_code })
    await line.getByRole('spinbutton', { name: /^发货数量/ }).fill('1')
    const shipped = action('/orders/' + fixture.order + '/ship/')
    await shipment.getByRole('button', { name: '确认发货', exact: true }).click()
    const shipResponse = await shipped
    expect(shipResponse.status(), await shipResponse.text()).toBe(201)
    const shipmentRecord = await shipResponse.json()
    const shipmentNumber = shipmentRecord.shipment_no
    expect(shipmentNumber).toBeTruthy()

    await go('/inventory-movements')
    await page.getByRole('button', { name: '新建库存调整', exact: true }).click()
    const adjustment = page.getByRole('dialog', { name: '新建手工库存流水' })
    await adjustment.getByLabel('手工流水类型').selectOption('return_in')
    const orderSearch = adjustment.getByPlaceholder('搜索并选择订单')
    await orderSearch.fill(fixture.order_no)
    await adjustment.getByText(/EVID-SO-001/).click()
    const skuSearch = adjustment.getByRole('searchbox', { name: '搜索 SKU、型号或描述' })
    await skuSearch.fill('CLOSEOUT-NO-SKU')
    await expect(adjustment.getByText('没有匹配的 SKU。')).toBeVisible()
    await skuSearch.fill(fixture.sku_code)
    await adjustment.locator('label').filter({ hasText: fixture.sku_code }).getByRole('checkbox').check()
    await adjustment.getByLabel(fixture.sku_code + ' 数量', { exact: true }).fill('1')
    await adjustment.getByLabel(fixture.sku_code + ' 仓库', { exact: true }).fill('默认仓')
    await adjustment.getByLabel(fixture.sku_code + ' 仓库类型', { exact: true }).selectOption('自有仓')
    await adjustment.getByLabel(fixture.sku_code + ' 批次或货位', { exact: true }).fill('EVID-RETURN-LOT-01')
    await adjustment.getByLabel(fixture.sku_code + ' 参考号', { exact: true }).fill('EVID-RETURN-REF-01')
    const returned = action('/inventory-movements/batch/')
    await adjustment.getByRole('button', { name: '保存 1 条流水', exact: true }).click()
    const returnResponse = await returned
    expect(returnResponse.ok(), await returnResponse.text()).toBeTruthy()
    await expect(adjustment).toHaveCount(0)

    for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
      for (const scale of [1, 1.25]) {
        zoom = scale
        await zoomControl.selectOption(String(zoom))
        await page.setViewportSize({ width, height })
        for (const [id, search, label] of [
          ['sales-out', shipmentNumber, '销售出库'],
          ['customer-return', 'EVID-RETURN-REF-01', 'EVID-RETURN-LOT-01'],
        ]) {
          await go('/inventory-movements?search=' + encodeURIComponent(search))
          const row = page.locator('.workspace-pane[aria-hidden="false"] tbody tr').filter({ hasText: search })
          await expect(row).toHaveCount(1)
          await row.click()
          const detail = page.getByRole('dialog', { name: /库存流水/ })
          const identity = detail.getByText(label, { exact: true }).first()
          await expect(identity).toBeVisible()
          await identity.scrollIntoViewIfNeeded()
          await expect(identity).toBeInViewport()
          expect(await page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
          const png = id + '-' + width + '-' + zoom * 100 + '.png'
          await page.screenshot({ path: path.join(output, png) })
          states.push({ id, width, height, zoom, png })
          await save()
        }
      }
    }
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
