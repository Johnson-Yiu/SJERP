import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect as playwrightExpect, test } from '@playwright/test'

const expect = playwrightExpect.configure({ timeout: 30000 })

test('quote revision recovers after a rejected save', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-revision-recovery')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-sales-completion-02/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: process.env,
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'revision-recovery-chrome'), {
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
        await go('/quotes?detail=' + fixture.quote)
        await page.getByRole('button', { name: '创建修订版', exact: true }).click()
        const editor = page.getByRole('form', { name: '报价编辑器' })
        const summary = editor.getByPlaceholder('例如：调整数量、价格、交期或付款条款')
        const value = '合成修订 ' + width + '-' + zoom * 100
        await summary.fill(value)
        const submit = editor.getByRole('button', { name: '保存报价', exact: true })
        const endpoint = url => url.pathname === '/api/quotes/' + fixture.quote + '/revise/'
        const write = response => endpoint(new URL(response.url())) && response.request().method() === 'POST'
        let release
        const gate = new Promise(resolve => { release = resolve })
        await page.route(endpoint, async route => {
          await gate
          await route.fulfill({ status: 400, json: { detail: '合成校验失败，请重试' } })
        }, { times: 1 })
        const rejected = page.waitForResponse(write)
        try {
          await submit.click()
          const pending = editor.locator('.quote-action-save')
          await expect(pending).toBeDisabled()
          await pending.scrollIntoViewIfNeeded()
          expect(await page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
          const png = 'revision-pending-' + width + '-' + zoom * 100 + '.png'
          const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
          await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
          states.push({ id: 'revision-pending', width, height, zoom, png })
          await save()
        } finally { release() }
        expect((await rejected).status()).toBe(400)
        await expect(summary).toHaveValue(value)
        await expect(submit).toBeEnabled()
        const accepted = page.waitForResponse(write)
        await submit.click()
        const response = await accepted
        expect(response.ok(), await response.text()).toBeTruthy()
        const child = await response.json()
        expect(child.id).not.toBe(fixture.quote)
        await go('/quotes?detail=' + child.id)
        await expect(page.getByRole('button', { name: '创建修订版', exact: true })).toBeVisible()
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
