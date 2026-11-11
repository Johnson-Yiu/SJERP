import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect as playwrightExpect, test } from '@playwright/test'

const expect = playwrightExpect.configure({ timeout: 30000 })

test('sales and purchase drafts recover after a rejected save', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-draft-recovery')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-final-state-closeout-03/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, CLOSEOUT_SALE_RETURN: '1' },
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'draft-recovery-chrome'), {
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

    const widths = process.env.CLOSEOUT_DRAFT_NARROW === '1' ? [[390, 844]] : [[1366, 768], [1440, 900], [390, 844]]
    const drafts = [
      ['sales', 'orders', fixture.order, '保存销售订单草稿'],
      ['purchase', 'purchase-orders', fixture.purchase, '保存采购草稿'],
    ].filter(([kind]) => !process.env.CLOSEOUT_DRAFT_KIND || kind === process.env.CLOSEOUT_DRAFT_KIND)
    for (const [width, height] of widths) {
      for (const scale of [1, 1.25]) {
        zoom = scale
        await zoomControl.selectOption(String(zoom))
        await page.setViewportSize({ width, height })
        for (const [kind, resource, id, saveLabel] of drafts) {
          await go('/' + resource + '?detail=' + id)
          await page.getByRole('button', { name: '编辑草稿', exact: true }).click()
          const field = kind === 'sales' ? page.getByLabel('交期天数') :
            page.getByRole('dialog', { name: '编辑采购草稿' }).getByPlaceholder('采购数量').first()
          const newValue = String(30 + states.length)
          await field.fill(newValue)
          const submit = page.getByRole('button', { name: saveLabel, exact: true })
          const endpoint = url => url.pathname === '/api/' + resource + '/' + id + '/'
          const write = response => endpoint(new URL(response.url())) && response.request().method() === 'PUT'
          let release
          const gate = new Promise(resolve => { release = resolve })
          await page.route(endpoint, async route => {
            if (route.request().method() !== 'PUT') return route.continue()
            await gate
            await route.fulfill({ status: 400, json: { detail: '合成校验失败，请重试' } })
          })
          const rejected = page.waitForResponse(write)
          void rejected.catch(() => {})
          try {
            try {
              await submit.click({ timeout: 15000 })
            } catch (error) {
              const png = kind + '-draft-save-obstructed-' + width + '-' + zoom * 100 + '.png'
              const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
              await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
              states.push({ id: kind + '-draft-save-obstructed', width, height, zoom, png })
              throw error
            }
            const pending = page.getByRole('button', { name: '保存中…', exact: true })
            await expect(pending).toBeDisabled()
            await pending.scrollIntoViewIfNeeded()
            expect(await page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
            const png = kind + '-draft-pending-' + width + '-' + zoom * 100 + '.png'
            const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
            await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
            states.push({ id: kind + '-draft-pending', width, height, zoom, png })
            await save()
          } finally { release() }
          expect((await rejected).status()).toBe(400)
          await page.unroute(endpoint)
          await expect(field).toHaveValue(newValue)
          await expect(submit).toBeEnabled()
          const accepted = page.waitForResponse(write)
          await submit.click()
          const response = await accepted
          expect(response.status(), await response.text()).toBe(200)
          await go('/' + resource + '?detail=' + id)
          await page.getByRole('button', { name: '编辑草稿', exact: true }).click()
          const storedValue = () => expect.poll(async () => Number(await field.inputValue())).toBe(Number(newValue))
          await storedValue()

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
