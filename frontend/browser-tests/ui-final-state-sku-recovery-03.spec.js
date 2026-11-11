import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect as playwrightExpect, test } from '@playwright/test'

const expect = playwrightExpect.configure({ timeout: 30000 })

test('SKU image upload can retry without repeating the SKU update', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-sku-recovery')
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

    await go('/skus')
    await page.getByRole('button', { name: '新建 SKU', exact: true }).click()
    const create = page.getByRole('dialog', { name: '新建 SKU' })
    await create.locator('select').first().selectOption(String(fixture.product))
    for (const [attribute, value] of [['色温', '4000K'], ['发光角度', '36'], ['外壳颜色', '黑']]) {
      const input = create.getByPlaceholder('输入' + attribute + '后按回车确认')
      await input.fill(value)
      await input.press('Enter')
    }
    await create.locator('.preview-table tbody input:not(:disabled)').check()
    const created = page.waitForResponse(response => response.url().endsWith('/api/skus/batch-create/') && response.request().method() === 'POST')
    await create.getByRole('button', { name: '保存并创建', exact: true }).click()
    const result = await created
    expect(result.status(), await result.text()).toBe(201)
    const [createdSku] = await result.json()
    await expect(create).toHaveCount(0)
    for (const [width, height] of [[1366, 768], [1440, 900], [390, 844]]) {
      for (const scale of [1, 1.25]) {
        zoom = scale
        await zoomControl.selectOption(String(zoom))
        await page.setViewportSize({ width, height })
        await go('/skus')
        const row = page.getByRole('row').filter({ hasText: createdSku.sku })
        const edit = page.getByRole('dialog', { name: '编辑 SKU' })
        const open = () => row.getByRole('button', { name: '编辑', exact: true }).click()
        await open()
        const bytes = await page.evaluate(() => {
          const canvas = document.createElement('canvas')
          canvas.width = 8
          canvas.height = 8
          const ctx = canvas.getContext('2d')
          ctx.fillStyle = '#c1322d'
          ctx.fillRect(0, 0, 8, 8)
          return canvas.toDataURL('image/png').split(',')[1]
        })
        await edit.locator('input[type=file]').setInputFiles({
          name: 'synthetic-' + width + '-' + zoom * 100 + '.png',
          mimeType: 'image/png', buffer: Buffer.from(bytes, 'base64'),
        })
        const skuPath = '/api/skus/' + createdSku.id + '/'
        const uploadPath = skuPath + 'image/'
        const upload = response => new URL(response.url()).pathname === uploadPath && response.request().method() === 'POST'
        const saveButton = edit.getByRole('button', { name: '保存 SKU', exact: true })
        const updates = []
        const countUpdates = request => {
          if (new URL(request.url()).pathname === skuPath && request.method() === 'PUT') updates.push(request)
        }
        page.on('request', countUpdates)
        try {
          await page.route(url => url.pathname === uploadPath, route =>
            route.fulfill({ status: 400, json: { detail: '合成图片上传失败' } }), { times: 1 })
          const rejected = page.waitForResponse(upload)
          await saveButton.click()
          expect((await rejected).status()).toBe(400)
          const message = edit.getByRole('alert').filter({ hasText: 'SKU 已更新，图片上传失败。请重试。' })
          await expect(message).toBeVisible()
          await expect(page.locator('.toast.error')).toHaveCount(0)
          const retry = edit.getByRole('button', { name: /重试上传/ })
          await retry.scrollIntoViewIfNeeded()
          await expect(message).toBeInViewport()
          expect(await page.evaluate(() => devicePixelRatio)).toBeCloseTo(zoom, 2)
          const png = 'sku-image-failed-' + width + '-' + zoom * 100 + '.png'
          const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
          await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
          states.push({ id: 'sku-image-failed', width, height, zoom, png })
          await save()
          await retry.click({ trial: true })
          await expect(message).toBeVisible()
          const uploaded = page.waitForResponse(upload)
          await retry.click()
          const response = await uploaded
          expect(response.ok(), await response.text()).toBeTruthy()
          await expect(edit).toHaveCount(0)
          expect(updates).toHaveLength(1)
          const stored = await page.request.get(new URL(skuPath, baseURL).href)
          expect(stored.ok()).toBeTruthy()
          const { image } = await stored.json()
          expect(image).toBeTruthy()
          await go('/skus')
          await open()
          await expect(edit.locator('.sku-image-picker img')).toHaveAttribute('src', image)
          await edit.locator('.sku-image-picker').getByRole('button', { name: '清除', exact: true }).click()
          const removal = response => new URL(response.url()).pathname === uploadPath && response.request().method() === 'DELETE'
          await page.route(url => url.pathname === uploadPath, route =>
            route.fulfill({ status: 400, json: { detail: '合成图片清除失败' } }), { times: 1 })
          const removalRejected = page.waitForResponse(removal)
          await saveButton.click()
          expect((await removalRejected).status()).toBe(400)
          const clearError = edit.getByRole('alert').filter({ hasText: 'SKU 已更新，图片清除失败。请重试。' })
          await expect(clearError).toBeVisible()
          const clearRetry = edit.getByRole('button', { name: '重试清除图片', exact: true })
          await clearRetry.click({ trial: true })
          await expect(clearError).toBeInViewport()
          await expect(clearError).toBeVisible()
          const cleared = page.waitForResponse(removal)
          await clearRetry.click()
          expect((await cleared).ok()).toBeTruthy()
          await expect(edit).toHaveCount(0)
          expect(updates).toHaveLength(2)
          await go('/skus')
          await open()
          await expect(edit.locator('.sku-image-picker img')).toHaveCount(0)
        } finally {
          page.off('request', countUpdates)
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
