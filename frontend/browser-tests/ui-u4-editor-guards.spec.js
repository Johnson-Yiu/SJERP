import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect as playwrightExpect, test } from '@playwright/test'

const expect = playwrightExpect.configure({ timeout: 30000 })

test('SKU and packaging recover from load failure and preserve keyboard draft choices', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-u4-editor-guards')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-final-state-closeout-03/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, PRODUCT_OPS_SKU_LIFECYCLE: '1' },
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'sku-recovery-chrome'), {
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
        for (const [url, endpoint, title] of [
          ['/skus', '/api/skus/', '新建 SKU'],
          ['/sku-packaging', '/api/packaging-templates/', '新建模板'],
        ]) {
          const matches = target => target.pathname === endpoint
          await page.route(matches, route => route.fulfill({ status: 503, json: { detail: '合成加载失败' } }))
          await go(url)
          const retry = page.getByRole('button', { name: '重新加载', exact: true }).first()
          await expect(retry).toBeVisible()
          await page.unroute(matches)
          const recovered = page.waitForResponse(response => matches(new URL(response.url())) && response.ok())
          await retry.press('Enter')
          await recovered
          const trigger = page.getByRole('button', { name: title, exact: true })
          await trigger.press('Enter')
          const editor = page.getByRole('dialog', { name: url === '/skus' ? title : '新建包装模板' })
          await expect(editor).toBeVisible()
          if (url === '/skus') {
            await editor.locator('select').first().selectOption(String(fixture.product))
          } else {
            await editor.getByLabel('模板名称', { exact: true }).fill('合成未保存模板')
          }
          const cancel = editor.locator('.modal-foot').getByRole('button', { name: '取消', exact: true }).last()
          await cancel.press('Enter')
          await page.getByRole('button', { name: '继续编辑', exact: true }).press('Enter')
          await expect(editor).toBeVisible()
          if (url === '/skus') {
            await expect(editor.locator('select').first()).toHaveValue(String(fixture.product))
          } else {
            await expect(editor.getByLabel('模板名称', { exact: true })).toHaveValue('合成未保存模板')
          }
          await cancel.press('Enter')
          const discard = page.getByRole('button', { name: '放弃修改', exact: true })
          await expect(discard).toBeVisible()
          await expect.poll(() => page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
          const png = endpoint.split('/')[2] + '-' + width + '-' + zoom * 100 + '.png'
          const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
          await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
          await discard.press('Enter')
          await expect(editor).toHaveCount(0)
          states.push({ endpoint, width, height, zoom, png })
          await save()
        }
      }
    }
  } catch (error) {
    failure = String(error)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
