import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect as playwrightExpect, test } from '@playwright/test'

const expect = playwrightExpect.configure({ timeout: 30000 })

test('inventory automatic sources and reversal entries are read-only while manual adjustment can reverse', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-inventory-source-actions')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-product-operations-completion-02/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, PRODUCT_OPS_INVENTORY_SOURCES: '1' },
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'inventory-source-actions-chrome'), {
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
    await settings.locator('settings-appearance-page select').filter({ has: settings.locator('option[value="1.25"]') }).selectOption('1.25', { timeout: 180000 })
    const go = () => page.goto(new URL('/inventory-movements?search=' + encodeURIComponent('合成一号仓'), baseURL).href, { waitUntil: 'commit', timeout: 240000 })
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
    const detail = page.getByRole('dialog', { name: '库存流水详情' })
    for (const source of ['SHIPMENT', 'RETURN', 'RECEIPT']) {
      const movementNo = 'EVID-INV-' + source
      const row = rows.filter({ hasText: movementNo })
      await expect(row).toContainText('系统自动')
      await expect(row.getByTitle('编辑', { exact: true })).toHaveCount(0)
      await expect(row.getByTitle('冲销', { exact: true })).toHaveCount(0)
      await row.getByTitle('查看详情', { exact: true }).click()
      await expect(detail).toContainText(movementNo)
      await expect(detail.getByRole('button', { name: '编辑主档', exact: true })).toHaveCount(0)
      await snap('inventory-source-' + source.toLowerCase())
      await detail.getByRole('button', { name: '关闭详情' }).click()
      await expect(detail).toHaveCount(0)
    }

    const row = rows.filter({ hasText: 'EVID-IM-0001' }).filter({ hasNotText: '冲销生成' })
    await expect(row).toContainText('手工登记')
    await expect(row.getByTitle('编辑', { exact: true })).toBeVisible()
    const reverse = row.getByTitle('冲销', { exact: true })
    await reverse.click()
    const confirm = page.getByRole('button', { name: '确认冲销', exact: true })
    await expect(confirm).toBeDisabled()
    await page.getByPlaceholder('请填写冲销原因').fill('EVID 核对手工调整冲销')
    await snap('manual-movement-reversal-confirmation')
    const [reversed] = await Promise.all([
      page.waitForResponse(r => r.url().endsWith('/reverse/') && r.request().method() === 'POST', { timeout: 75000 }),
      confirm.click(),
    ])
    expect(reversed.ok(), await reversed.text()).toBeTruthy()
    await expect(row).toContainText('已冲销')
    const generated = rows.filter({ hasText: '冲销生成' })
    await expect(generated).toHaveCount(1)
    for (const locked of [row, generated]) {
      await expect(locked.getByTitle('编辑', { exact: true })).toHaveCount(0)
      await expect(locked.getByTitle('冲销', { exact: true })).toHaveCount(0)
    }
    await generated.scrollIntoViewIfNeeded()
    await snap('manual-movement-and-reversal-readonly')
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
