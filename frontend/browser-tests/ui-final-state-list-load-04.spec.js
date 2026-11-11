import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect as playwrightExpect, test } from '@playwright/test'

const expect = playwrightExpect.configure({ timeout: 30000 })

test('customer, quote and order lists distinguish loading, failure and real empty data', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-list-load')
  await mkdir(output, { recursive: true })
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'list-load-chrome'), {
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

    for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
      for (const scale of [1, 1.25]) {
        zoom = scale
        await zoomControl.selectOption(String(zoom))
        await page.setViewportSize({ width, height })
        for (const resource of ['customers', 'quotes', 'orders']) {
          const endpoint = url => url.pathname === '/api/' + resource + '/'
          let release
          const gate = new Promise(resolve => { release = resolve })
          await context.route(endpoint, async route => {
            await gate
            await route.fulfill({ status: 400, json: { detail: '合成列表读取失败' } })
          })
          async function capture(state, element) {
            await element.scrollIntoViewIfNeeded()
            await expect(element).toBeInViewport()
            expect(await page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
            const png = resource + '-' + state + '-' + width + '-' + zoom * 100 + '.png'
            const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
            await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
            states.push({ resource, state, width, height, zoom, png })
            await save()
          }
          try {
            await go('/' + resource)
            await capture('loading', page.locator('.page-load-state-loading'))
            await expect(page.locator('.list-empty-state')).toHaveCount(0)
          } finally { release() }
          const error = page.locator('.page-load-state-error').filter({ hasText: '合成列表读取失败' })
          await capture('rejected', error)
          await expect(page.locator('.list-empty-state')).toHaveCount(0)
          await context.unroute(endpoint)
          const recovered = page.waitForResponse(response => endpoint(new URL(response.url())) && response.ok())
          await error.getByRole('button', { name: '重新加载' }).click()
          const response = await recovered
          expect((await response.json()).results).toEqual([])
          await expect(error).toHaveCount(0)
          await capture('empty', page.locator('.list-empty-state'))
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
