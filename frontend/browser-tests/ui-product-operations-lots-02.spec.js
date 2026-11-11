import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('same warehouse movements retain independent lot details and return to the filtered list', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-same-warehouse-lots')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-product-operations-completion-02/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, PRODUCT_OPS_LOTS: '1' },
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'same-warehouse-lots-chrome'), {
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
    page.setDefaultTimeout(45000)
    const cdp = await context.newCDPSession(page)
    browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    await settings.goto('chrome://settings/appearance', { waitUntil: 'domcontentloaded', timeout: 100000 })
    await settings.locator('settings-appearance-page select').filter({ has: settings.locator('option[value="1.25"]') }).selectOption('1.25')
    const go = () => page.goto(new URL('/inventory-movements?search=' + encodeURIComponent('合成一号仓'), baseURL).href, { waitUntil: 'domcontentloaded', timeout: 100000 })
    async function snap(id, extra = {}) {
      const dpr = await page.evaluate(() => devicePixelRatio)
      expect(dpr).toBeCloseTo(1.25, 2)
      const png = id + '-390-125.png'
      const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
      states.push({ id, width: 390, height: 844, zoom: 1.25, dpr, png, ...extra })
      await save()
    }
    await go()
    const rows = page.locator('.workspace-pane[aria-hidden="false"] tbody tr')
    await expect(rows).toHaveCount(2)
    await expect(rows.filter({ hasText: 'EVID-IM-0002' })).toHaveCount(0)
    await snap('same-warehouse-two-movements')
    for (const sequence of ['01', '03']) {
      const row = rows.filter({ hasText: 'EVID-IM-00' + sequence })
      const number = 'EVID-IM-00' + sequence
      const expectedLot = 'EVID-LOT-20261110-A-' + sequence
      const [movement] = await Promise.all([
        page.waitForResponse(r => new URL(r.url()).pathname.split('/').length === 5 && new URL(r.url()).pathname.startsWith('/api/inventory-movements/'), { timeout: 75000 }),
        row.click(),
      ])
      expect(movement.ok()).toBeTruthy()
      expect(await movement.json()).toMatchObject({ movement_no: number, lot_reference: expectedLot, warehouse: '合成一号仓' })
      const detail = page.getByRole('dialog', { name: '库存流水详情' })
      await expect(detail).toBeVisible()
      await expect(detail).toContainText('合成一号仓')
      await expect(detail).toContainText(number)
      await expect(detail.getByRole('button', { name: '编辑主档' })).toHaveCount(0)
      await detail.getByText('合成一号仓', { exact: true }).scrollIntoViewIfNeeded()
      await snap('same-warehouse-lot-' + sequence, { lotFromApi: expectedLot, lotShownInDrawer: await detail.getByText(expectedLot, { exact: true }).count() > 0 })
      await detail.getByRole('button', { name: '关闭详情' }).click()
      await expect(detail).toHaveCount(0)
      await expect(page.getByRole('textbox', { name: '搜索库存流水' })).toHaveValue('合成一号仓')
      await expect(rows).toHaveCount(2)
    }
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
