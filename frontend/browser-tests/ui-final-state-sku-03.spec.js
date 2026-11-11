import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('SKU combinations persist, duplicate candidates are excluded, and images can be replaced and removed', async ({ baseURL }) => {
  test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== path.basename(fileURLToPath(import.meta.url)),
    'Requires a dedicated seeded database; run this spec through the isolated runner.')
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-sku-lifecycle')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-final-state-closeout-03/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, PRODUCT_OPS_SKU_LIFECYCLE: '1' },
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'sku-lifecycle-chrome'), {
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
    const go = () => page.goto(new URL('/skus', baseURL).href, { waitUntil: 'domcontentloaded', timeout: 100000 })
    const getSku = async id => (await page.request.get(new URL('/api/skus/' + id + '/', baseURL).href)).json()
    async function snap(id, extra = {}) {
      const dpr = await page.evaluate(() => devicePixelRatio)
      expect(dpr).toBeCloseTo(1.25, 2)
      const png = id + '-390-125.png'
      const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      await writeFile(path.join(output, png), Buffer.from(data, 'base64'))
      states.push({ id, width: 390, height: 844, zoom: 1.25, dpr, png, ...extra })
      await save()
    }
    const group = [['色温', ['3000K', '4000K']], ['发光角度', ['24', '36']], ['外壳颜色', ['黑']]]
    async function configure() {
      await page.getByRole('button', { name: '新建 SKU', exact: true }).click()
      const dialog = page.getByRole('dialog', { name: '新建 SKU' })
      await dialog.locator('select').first().selectOption(String(fixture.product))
      for (const [attribute, values] of group) {
        const input = dialog.getByPlaceholder('输入' + attribute + '后按回车确认')
        for (const value of values) {
          await input.fill(value)
          await input.press('Enter')
        }
      }
      return dialog
    }

    await go()
    const create = await configure()
    const submit = create.getByRole('button', { name: '保存并创建', exact: true })
    const candidates = create.locator('.preview-table tbody input:not(:disabled)')
    await expect(candidates).toHaveCount(4)
    for (const candidate of await candidates.all()) await candidate.check()
    await expect(create.getByRole('button', { name: '创建 4 个 SKU', exact: true })).toBeEnabled()
    let release
    const held = new Promise(resolve => { release = resolve })
    const endpoint = '**/api/skus/batch-create/'
    await page.route(endpoint, async route => {
      await held
      await route.continue()
    }, { times: 1 })
    const posted = page.waitForResponse(response => response.url().endsWith('/api/skus/batch-create/') && response.request().method() === 'POST', { timeout: 75000 })
    try {
      await submit.click()
      const busy = create.getByRole('button', { name: '保存中…', exact: true })
      await expect(busy).toBeDisabled()
      await snap('sku-batch-submitting', { method: 'temporarily held outgoing POST, then forwarded to real backend' })
    } finally {
      release()
    }
    const response = await posted
    expect(response.status(), await response.text()).toBe(201)
    const created = await response.json()
    expect(created).toHaveLength(4)
    expect(new Set(created.map(row => row.sku)).size).toBe(4)
    await expect(create).toHaveCount(0)
    const selected = created.find(row => row.specification.includes('4000K') && row.specification.includes('36'))
    expect(selected).toBeTruthy()
    const saved = await getSku(selected.id)
    expect(saved).toMatchObject({ sku: selected.sku, specification: selected.specification })
    await go()
    const duplicate = await configure()
    const preview = duplicate.locator('.preview-section')
    await expect(preview).toContainText('已存在 4 项')
    await expect(duplicate.getByRole('button', { name: '创建 0 个 SKU', exact: true })).toBeVisible()
    await preview.scrollIntoViewIfNeeded()
    await snap('sku-duplicate-combinations')
    await duplicate.getByRole('button', { name: '关闭 SKU 窗口' }).click()
    await page.getByRole('button', { name: '放弃修改', exact: true }).click()
    await go()

    const row = page.getByRole('row').filter({ hasText: selected.sku })
    const edit = page.getByRole('dialog', { name: '编辑 SKU' })
    const openEdit = async () => {
      await row.getByRole('button', { name: '编辑', exact: true }).click()
      await expect(edit).toBeVisible()
    }
    const submitEdit = () => edit.getByRole('button', { name: '保存 SKU', exact: true }).click()
    async function imageBuffer(color) {
      const data = await page.evaluate(fill => {
        const canvas = document.createElement('canvas')
        canvas.width = canvas.height = 8
        const graphics = canvas.getContext('2d')
        graphics.fillStyle = fill
        graphics.fillRect(0, 0, 8, 8)
        return canvas.toDataURL('image/png').split(',')[1]
      }, color)
      return Buffer.from(data, 'base64')
    }
    const list = url => url.pathname === '/api/skus/'
    let previousImage
    for (const [name, color] of [['sku-initial.png', 'red'], ['sku-replacement.png', 'blue']]) {
      await openEdit()
      const code = edit.locator('.sku-basics input[readonly]:not([placeholder])')
      await expect(code).toHaveValue(selected.sku)
      const file = { name, mimeType: 'image/png', buffer: await imageBuffer(color) }
      await edit.locator('input[type=file]').setInputFiles(file)
      const image = edit.locator('.sku-image-picker img')
      await expect(image).toBeVisible()
      await image.scrollIntoViewIfNeeded()
      await snap(name.replace('.png', '-selected'))
      let releaseList
      const pendingList = new Promise(resolve => { releaseList = resolve })
      await page.route(list, async route => { await pendingList; await route.continue() }, { times: 1 })
      const [upload] = await Promise.all([
        page.waitForResponse(r => r.url().endsWith('/api/skus/' + selected.id + '/image/') && r.request().method() === 'POST', { timeout: 75000 }),
        submitEdit(),
      ])
      expect(upload.ok(), await upload.text()).toBeTruthy()
      await expect(edit).toHaveCount(0)
      const current = await getSku(selected.id)
      expect(current.image).toBeTruthy()
      expect(current.image).not.toBe(previousImage)
      previousImage = current.image
      try {
        await openEdit()
        await expect(edit.locator('.sku-image-picker img')).toHaveAttribute('src', current.image)
        await edit.getByRole('button', { name: '关闭 SKU 窗口' }).click()
      } finally { releaseList() }
    }
    await openEdit()
    await edit.locator('.sku-image-picker').getByRole('button', { name: '清除', exact: true }).click()
    const listFailed = page.waitForResponse(r => list(new URL(r.url())) && r.status() === 400)
    await page.route(list, route => route.fulfill({ status: 400, json: { detail: '合成列表刷新失败' } }), { times: 1 })
    const [removal] = await Promise.all([
      page.waitForResponse(r => r.url().endsWith('/api/skus/' + selected.id + '/image/') && r.request().method() === 'DELETE', { timeout: 75000 }),
      submitEdit(),
    ])
    expect(removal.ok(), await removal.text()).toBeTruthy()
    await expect(edit).toHaveCount(0)
    expect((await getSku(selected.id)).image).toBeFalsy()
    await listFailed
    await openEdit()
    await expect(edit.locator('.sku-image-picker img')).toHaveCount(0)
    await edit.locator('.sku-image-picker').scrollIntoViewIfNeeded()
    await snap('sku-image-removed-reopened')
    await edit.getByRole('button', { name: '关闭 SKU 窗口' }).click()
    await row.getByRole('button', { name: '历史版本', exact: true }).click()
    const versions = page.getByRole('dialog', { name: 'SKU 历史版本' })
    await expect(versions).toContainText('暂无关键字段变更记录')
    await snap('sku-version-empty-after-image-only')
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
