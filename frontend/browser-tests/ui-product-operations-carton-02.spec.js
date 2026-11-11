import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, expect, test } from '@playwright/test'

test('shared carton policy update requires confirmation and invalidates linked SKU verification', async ({ baseURL }) => {
  test.setTimeout(2400000)
  const source = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const output = path.resolve(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'chrome-shared-carton')
  await mkdir(output, { recursive: true })
  const seed = fileURLToPath(new URL('../../docs/uat-evidence/ui-product-operations-completion-02/seed.py', import.meta.url))
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [seed], {
    cwd: path.resolve('../backend'), encoding: 'utf8', env: { ...process.env, PRODUCT_OPS_PACKAGING: '1' },
  }))
  const root = process.env.ISOLATED_TEST_ROOT
  const context = await chromium.launchPersistentContext(path.join(root, 'shared-carton-chrome'), {
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
    const go = () => page.goto(new URL('/sku-packaging', baseURL).href, { waitUntil: 'domcontentloaded', timeout: 100000 })
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
    const row = page.getByRole('row').filter({ hasText: '合成长箱规' })
    const edit = page.getByRole('dialog', { name: '编辑包装模板' })
    const fetchTemplate = async () => {
      const response = await page.request.get(new URL('/api/packaging-templates/' + fixture.template + '/', baseURL).href)
      expect(response.ok()).toBeTruthy()
      return response.json()
    }
    const loadProfiles = () => Promise.all(fixture.packaged_skus.map(async id => {
      const response = await page.request.get(new URL('/api/skus/' + id + '/', baseURL).href)
      expect(response.ok()).toBeTruthy()
      return (await response.json()).packaging
    }))
    expect((await fetchTemplate()).linked_sku_count).toBe(2)
    const original = await loadProfiles()
    expect(original.map(profile => profile.status)).toEqual(['VERIFIED', 'VERIFIED'])
    await row.getByRole('button', { name: '编辑', exact: true }).click()
    await edit.getByLabel('尾货策略', { exact: true }).selectOption('MANUAL')
    await edit.getByRole('button', { name: '保存模板', exact: true }).click()
    const confirmation = page.getByRole('button', { name: '确认继续', exact: true })
    await expect(confirmation).toBeVisible()
    await expect(page.getByText(/该模板已关联 2 个 SKU/)).toBeVisible()
    await snap('carton-linked-change-confirmation')
    const [changed] = await Promise.all([
      page.waitForResponse(r => r.url().endsWith('/api/packaging-templates/' + fixture.template + '/') && r.request().method() === 'PUT', { timeout: 75000 }),
      confirmation.click(),
    ])
    expect(changed.ok(), await changed.text()).toBeTruthy()
    await expect(edit).toHaveCount(0)
    expect((await fetchTemplate()).partial_carton_policy).toBe('MANUAL')
    const refreshed = await loadProfiles()
    expect(refreshed.map(profile => profile.template)).toEqual(original.map(profile => profile.template))
    expect(refreshed.every(profile => profile.status !== 'VERIFIED')).toBeTruthy()
    await go()
    await row.getByRole('button', { name: '编辑', exact: true }).click()
    await expect(edit.getByLabel('尾货策略', { exact: true })).toHaveValue('MANUAL')
    await edit.getByLabel('尾货策略', { exact: true }).scrollIntoViewIfNeeded()
    await snap('carton-tail-policy-reopened')
  } catch (error) {
    failure = String(error.message)
    throw error
  } finally {
    await save()
    await context.close()
  }
})
