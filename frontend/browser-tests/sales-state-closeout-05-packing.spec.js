import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('S5 checks order party conditions and reverses a packed shipment', async ({ baseURL }) => {
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
  const { identifiers, packingOrders } = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.join(output, 'seed.py'), '--packing'], {
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


    let index = 0
    const workbench = page.getByRole('dialog', { name: '订单工作台' })
    const party = workbench.locator('.party-details-panel')
    for (const zoom of [1, 1.25]) {
      await settings.bringToFront()
      await zoomControl.selectOption(String(zoom), { timeout: 90000 })
      await page.bringToFront()
      for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
        const fixture = packingOrders[index++]
        await page.setViewportSize({ width, height })
        const open = (id, tab) => page.goto(new URL(`/orders?detail=${id}&tab=${tab}`, baseURL).href, { waitUntil: 'commit', timeout: 90000 })
        await open(identifiers.draft, 'overview')
        const metrics = await page.evaluate(() => ({ dpr: devicePixelRatio, cssWidth: innerWidth }))
        expect(metrics.dpr).toBe(zoom)
        expect(metrics.cssWidth).toBeCloseTo(width / zoom, 0)
        const capture = async (state, locator) => {
          await locator.scrollIntoViewIfNeeded()
          const screenshot = `${state}-${width}-${zoom * 100}.png`
          const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' })
          await writeFile(path.join(screenshots, screenshot), Buffer.from(data, 'base64'))
          return screenshot
        }
        const draftSave = party.getByRole('button', { name: '保存双方资料' })
        await expect(draftSave).toBeEnabled()
        await expect(workbench.getByRole('button', { name: '查看主体版本与更正' })).toHaveCount(0)
        const draftParty = await capture('so-04-draft-party', draftSave)
        await open(fixture.order, 'overview')
        const snapshot = workbench.locator('.party-snapshot-card')
        await expect(snapshot).toContainText('S5 合成商业展厅照明采购及设施维护服务有限公司')
        await expect(draftSave).toHaveCount(0)
        const versions = workbench.getByRole('button', { name: '查看主体版本与更正' })
        await versions.click()
        await expect(workbench.getByRole('heading', { name: '当前有效主体资料' })).toBeVisible()
        const requestCorrection = workbench.getByRole('button', { name: '提交更正申请' })
        await expect(requestCorrection).toBeEnabled()
        await expect(workbench.getByRole('button', { name: '申请更换法律主体' })).toBeEnabled()
        const formalParty = await capture('so-04-formal-party', requestCorrection)

        await open(fixture.order, 'packing')
        const card = page.locator('.actual-shipment-card').filter({ hasText: fixture.number })
        await card.getByRole('button', { name: '新增箱', exact: true }).click()
        const packing = page.getByRole('dialog', { name: /^新增实际装箱记录/ })
        await packing.getByLabel('SKU 1', { exact: true }).selectOption({ index: 1 })
        await packing.getByLabel('实际装箱数量 1').fill('2')
        const endpoint = (url, action) => new URL(url).pathname === `/api/shipments/${fixture.shipment}/${action}/`
        const posted = action => page.waitForResponse(response => endpoint(response.url(), action) && response.request().method() === 'POST')
        const created = posted('packages')
        await packing.getByRole('button', { name: '保存实际装箱' }).click()
        const packageResponse = await created
        expect(packageResponse.status(), await packageResponse.text()).toBe(201)
        await expect(card.locator('.actual-carton-card')).toHaveCount(1)
        const facts = () => JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [path.join(output, 'shipment-facts.py'), String(fixture.shipment)], {
          cwd: path.join(repository, 'backend'), encoding: 'utf8',
        }))
        const before = facts()
        expect(before.cartons).toHaveLength(1)
        expect(before.cartons[0].quantities.map(Number)).toEqual([2])
        expect(before.reversalCount).toBe(0)
        await open(fixture.order, 'fulfillment')
        const history = workbench.locator('.shipment-history-card').filter({ hasText: fixture.number })
        await history.getByRole('button', { name: '冲销', exact: true }).click()
        const reversal = page.locator('.trade-shipment-dialog').filter({ hasText: '冲销发货' })
        const submit = reversal.getByRole('button', { name: '确认冲销' })
        await expect(submit).toBeDisabled()
        await reversal.getByLabel('冲销原因').fill('S5 合成装箱发货冲销')
        const reversed = posted('reverse')
        await submit.click()
        const reversalResponse = await reversed
        expect(reversalResponse.status(), await reversalResponse.text()).toBe(200)
        await expect(history).toContainText('已冲销')
        await expect(history.getByRole('button', { name: '冲销', exact: true })).toHaveCount(0)
        const cancelled = await capture('so-05-reversed', history)
        const csrf = (await context.cookies()).find(cookie => cookie.name === 'csrftoken')
        const duplicate = await page.request.post(new URL(`/api/shipments/${fixture.shipment}/reverse/`, baseURL).href, {
          headers: { 'X-CSRFToken': csrf.value, Referer: baseURL },
          data: { reason: 'S5 重复冲销' },
        })
        expect(duplicate.status()).toBe(400)
        expect(await duplicate.text()).toContain('不能重复操作')
        await open(fixture.order, 'packing')
        await expect(card.locator('.actual-carton-card')).toHaveCount(1)
        await expect(card.getByRole('button', { name: '新增箱', exact: true })).toHaveCount(0)
        const reopened = await capture('so-05-packing-reopened', card)
        const after = facts()
        expect(after.cartons).toEqual(before.cartons)
        expect(after.outbound).toEqual(before.outbound)
        expect(after).toMatchObject({
          status: 'cancelled', orderStatus: 'confirmed', reason: 'S5 合成装箱发货冲销', reversalCount: 1,
          reversal: { type: 'adjust_in', order: fixture.order, source: fixture.number, reference: before.outbound.number, sameLocation: true },
        })
        expect(Number(after.reversal.quantity)).toBe(2)
        expect(Number(after.stock.actual_quantity) - Number(before.stock.actual_quantity)).toBe(2)
        results.push({ width, height, zoom, ...metrics, draftParty, formalParty, cancelled, reopened, before, after, duplicate: duplicate.status() })
      }
    }
  } catch (error) {
    failure = String(error.stack || error)
    throw error
  } finally {
    await writeFile(path.join(output, 'so-04-so-05.json'), JSON.stringify({ source, browser, results, failure }, null, 2) + '\n')
    await context.close()
  }
})
