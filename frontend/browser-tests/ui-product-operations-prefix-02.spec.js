import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('prefix preview, cancellation, server refusal and apply preserve SKU identity', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const root = process.env.ISOLATED_TEST_ROOT
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const evidence = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT)
  const output = path.join(evidence, 'chrome-prefix-version')
  await mkdir(output, { recursive: true })
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [fileURLToPath(new URL('../../docs/uat-evidence/ui-product-operations-completion-02/seed.py', import.meta.url))], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, PRODUCT_OPS_PREFIX: '1' },
  }))
  const context = await chromium.launchPersistentContext(path.join(root, 'product-prefix-chrome'), {
    channel: 'chrome', viewport: { width: 1440, height: 900 },
  })
  const states = []
  let browser
  let failure
  const save = () => writeFile(path.join(output, 'run.json'), JSON.stringify({ source, browser, api: 'real isolated Django', states, failure }, null, 2) + '\n')
  try {
    const auth = JSON.parse(await readFile(path.join(root, 'codex-auth.json'), 'utf8'))
    await context.addCookies(auth.cookies)
    const settings = context.pages()[0]
    const page = await context.newPage()
    page.setDefaultTimeout(30000)
    const cdp = await context.newCDPSession(page)
    browser = (await cdp.send('Browser.getVersion')).product
    expect(browser).toMatch(/^Chrome\//)
    const loadProduct = async () => (await page.request.get(new URL('/api/products/' + fixture.product + '/', baseURL).href)).json()
    const loadSku = async () => (await page.request.get(new URL('/api/skus/' + fixture.sku + '/', baseURL).href)).json()
    const original = await loadSku()
    const prefix = page.getByPlaceholder('如：BTY、COB320、SMD120')
    const form = page.getByRole('dialog', { name: '编辑产品' })
    const review = page.locator('.prefix-review-modal')
    async function snap(id, zoom, width, height) {
      const dpr = await page.evaluate(() => devicePixelRatio)
      expect(dpr).toBeCloseTo(zoom, 2)
      const png = id + '-' + width + '-' + zoom * 100 + '.png'
      const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
      states.push({ id, width, height, zoom, dpr, png })
      await save()
    }
    async function write(id, action, status, trigger) {
      const [response] = await Promise.all([
        page.waitForResponse(r => new URL(r.url()).pathname === '/api/products/' + fixture.product + '/' + action + '/'
          && r.request().method() === 'POST', { timeout: 75000 }),
        trigger.click(),
      ])
      states.push({ id, httpStatus: response.status() })
      await save()
      expect(response.status()).toBe(status)
    }
    await page.goto(new URL('/products', baseURL).href, { waitUntil: 'commit', timeout: 100000 })
    const row = page.getByRole('row').filter({ hasText: 'EVID-P001' })
    await row.getByRole('button', { name: '编辑产品' }).click()
    await prefix.fill('EIVDUPE')
    await write('prefix-refused', 'sales-model-prefix-preview', 400, form.getByRole('button', { name: '保存', exact: true }))
    await expect(form.getByRole('alert')).toBeVisible()
    await snap('prefix-refused', 1, 1440, 900)
    await prefix.fill('EVIDNEW')
    await write('prefix-preview', 'sales-model-prefix-preview', 200, form.getByRole('button', { name: '保存', exact: true }))
    await expect(review).toContainText('EVIDNEW')
    await settings.goto('chrome://settings/appearance', { waitUntil: 'domcontentloaded', timeout: 100000 })
    const zoomControl = settings.locator('settings-appearance-page select').filter({
      has: settings.locator('option[value="1.25"]'),
    })
    for (const zoom of [1, 1.25]) {
      await zoomControl.selectOption(String(zoom))
      for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
        await page.setViewportSize({ width, height })
        if (width === 390) {
          await expect.poll(() => page.locator('.sidebar').evaluate(element => element.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
        }
        await review.getByRole('button', { name: '确认更新' }).scrollIntoViewIfNeeded()
        await snap('prefix-preview', zoom, width, height)
      }
    }
    await review.getByRole('button', { name: '取消', exact: true }).click()
    await expect(review).toHaveCount(0)
    expect((await loadProduct()).sales_model_prefix).toBe('EVIDOLD')
    expect((await loadSku()).sales_model).toBe(original.sales_model)
    await snap('prefix-cancel-keeps-editor', 1.25, 390, 844)
    await write('prefix-preview-again', 'sales-model-prefix-preview', 200, form.getByRole('button', { name: '保存', exact: true }))
    await write('prefix-apply', 'sales-model-prefix-apply', 200, review.getByRole('button', { name: '确认更新' }))
    await expect(form).toHaveCount(0)
    expect((await loadProduct()).sales_model_prefix).toBe('EVIDNEW')
    expect(await loadSku()).toMatchObject({ sku: original.sku, sales_model: expect.stringMatching(/^EVIDNEW/) })
    await expect(row).toContainText('EVIDNEW')
    await snap('prefix-apply-saved', 1.25, 390, 844)
    await page.goto(new URL('/skus', baseURL).href, { waitUntil: 'commit', timeout: 100000 })
    const changedSku = page.getByRole('row').filter({ hasText: original.sku })
    const [history] = await Promise.all([
      page.waitForResponse(r => r.url().endsWith('/api/skus/' + fixture.sku + '/versions/'), { timeout: 75000 }),
      changedSku.getByRole('button', { name: '历史版本', exact: true }).click(),
    ])
    expect(history.ok()).toBeTruthy()
    expect((await history.json()).some(version => version.sales_model_snapshot === original.sales_model)).toBeTruthy()
    const versions = page.getByRole('dialog', { name: 'SKU 历史版本' })
    await expect(versions).toContainText(original.sales_model)
    await versions.getByText(original.sales_model, { exact: true }).scrollIntoViewIfNeeded()
    await snap('sku-version-preserves-old-model', 1.25, 390, 844)
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
