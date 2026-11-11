import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect as playwrightExpect, test } from '@playwright/test'

const expect = playwrightExpect.configure({ timeout: 30000 })

test('finance list headers, tail actions and details remain usable at native 125%', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-finance-layout')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-final-state-closeout-03/seed.py', import.meta.url))
  execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, CLOSEOUT_FINANCE_LAYOUT: '1' },
  })
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'finance-layout-chrome'), {
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

    for (const [width, height] of [[1440, 900], [390, 844]]) {
      await page.setViewportSize({ width, height })
      for (const [route, key, detailName] of [
        ['/rmb-cash-events', 'EVID-BANK-CLOSEOUT', 'EVID-BANK-CLOSEOUT'],
        ['/transactions', 'EVID-TRANSACTION-CLOSEOUT', '财务流水详情'],
      ]) {
        await go(route)
        const row = page.getByRole('row').filter({ hasText: key })
        await expect(row).toBeVisible()
        const table = row.locator('xpath=ancestor::table[1]')
        await expect(table.getByRole('columnheader', { name: '操作' })).toBeVisible()
        const action = row.getByRole('button', { name: /详情/ }).first()
        await action.scrollIntoViewIfNeeded()
        await expect(action).toBeInViewport()
        const metrics = await page.evaluate(() => ({
          dpr: devicePixelRatio, width: innerWidth, documentWidth: document.documentElement.scrollWidth,
        }))
        expect(metrics.dpr).toBeCloseTo(zoom, 2)
        expect(metrics.documentWidth).toBeLessThanOrEqual(metrics.width)
        const prefix = route.slice(1) + '-' + width
        async function capture(stage) {
          const png = prefix + '-' + stage + '.png'
          const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
          await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
          states.push({ png, width, height, zoom, metrics })
          await save()
        }
        await capture('tail-action')
        await action.click()
        await expect(page.getByRole('dialog', { name: detailName })).toBeVisible()
        await capture('detail')
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
