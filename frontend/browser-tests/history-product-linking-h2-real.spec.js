import { test as base, expect, chromium } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'

const nativeZoom = Number(process.env.H2_NATIVE_ZOOM || 100)
const test = base.extend({
  context: async ({ context, baseURL, viewport }, use) => {
    if (nativeZoom === 100) {
      await use(context)
      return
    }
    const profile = await mkdtemp(path.join(process.env.ISOLATED_TEST_ROOT, 'h2-chrome-'))
    try {
      const chrome = await chromium.launchPersistentContext(profile, { channel: 'chrome', baseURL, viewport })
      try {
        await chrome.addCookies((await context.storageState()).cookies)
        const settings = chrome.pages()[0]
        await settings.setViewportSize({ width: 1440, height: 900 })
        await settings.goto('chrome://settings/appearance')
        await settings.getByRole('combobox', { name: /网页缩放|Page zoom/ }).selectOption({ label: `${nativeZoom}%` })
        await use(chrome)
      } finally {
        await chrome.close()
      }
    } finally {
      await rm(profile, { recursive: true, force: true })
    }
  },
})

test.use({ channel: 'chrome', viewport: { width: Number(process.env.H2_VIEWPORT_WIDTH || 1440), height: 900 } })

test('H2 controlled candidate selection, specification recovery, audit, analysis and CSV', async ({ page, browser }, info) => {
  test.setTimeout(300_000)
  page.setDefaultTimeout(30_000)
  const output = process.env.H2_EVIDENCE_ROOT || info.outputPath('h2')
  await mkdir(output, { recursive: true })
  const capture = async name => {
    const destination = path.join(output, name + '.png')
    if (nativeZoom === 100) {
      await page.screenshot({ path: destination })
      return
    }
    const session = await page.context().newCDPSession(page)
    try {
      const screenshot = await session.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      await writeFile(destination, Buffer.from(screenshot.data, 'base64'))
    } finally {
      await session.detach()
    }
  }
  const fixture = JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON, [
    path.resolve('../docs/uat-evidence/history-product-linking-fixes-02/seed-browser.py'),
  ], { cwd: path.resolve('../backend'), env: process.env, encoding: 'utf8' }).trim().split('\n').at(-1))

  await page.goto('/history-takeover?application=' + fixture.candidate, { waitUntil: 'domcontentloaded' })
  const effective = await page.evaluate(() => ({ width: innerWidth, scale: devicePixelRatio }))
  expect(effective.scale).toBeCloseTo(nativeZoom / 100)
  expect(Math.abs(effective.width - page.viewportSize().width / effective.scale)).toBeLessThan(2)
  await page.getByRole('button', { name: /H2-CANDIDATE/ }).click()
  const choose = page.getByRole('button', { name: '选用此候选' })
  await expect(choose).toBeVisible()
  await expect(page.getByText('正式灯具 B · B · 24W · pcs', { exact: true }).first()).toBeVisible()
  await choose.scrollIntoViewIfNeeded()
  await capture('candidate')
  await choose.click()
  await expect(page.getByLabel('选择现有对象')).toHaveValue('B')
  await expect(page.getByRole('button', { name: '保存关联并重新预检' })).toBeDisabled()
  await page.getByLabel('关联依据').fill('已与合成旧单的型号和规格核对')
  await page.getByLabel('关联依据').scrollIntoViewIfNeeded()
  await capture('candidate-selected')
  const saveMapping = page.waitForResponse(response => response.url().includes('/resolve-master/') && response.request().method() === 'POST')
  await page.getByRole('button', { name: '保存关联并重新预检' }).click()
  expect((await saveMapping).status()).toBe(200)
  await expect(page.getByText('已登记主档关联')).toBeVisible()

  await page.goto('/history-takeover?application=' + fixture.archived, { waitUntil: 'domcontentloaded' })
  await page.getByText('历史商品关联', { exact: true }).first().click()
  await page.getByRole('checkbox', { name: 'A1', exact: true }).check()
  await page.getByRole('button', { name: /处理所选商品/ }).click()
  const dialog = page.getByRole('dialog')
  const sku = dialog.getByLabel('正式 SKU', { exact: true })
  const target = sku.locator('option').filter({ hasText: /^B · 正式灯具 B/ })
  await expect(target).toHaveCount(1)
  await sku.selectOption(await target.getAttribute('value'))
  await expect(dialog.getByRole('button', { name: '生成预览' })).toBeEnabled()
  await dialog.getByRole('button', { name: '生成预览' }).click()
  await expect(dialog.getByRole('alert')).toHaveText(/关联未保存/)
  await capture('missing-specification-conflict')
  await dialog.getByLabel(/补核规格/).fill('24 W')
  await dialog.getByLabel(/原因/).fill('合成检验单 REF-H2-24')
  await dialog.getByRole('button', { name: '生成预览' }).click()
  await expect(dialog.getByRole('region', { name: '关联预览' })).toContainText('影响 1 条明细')
  await capture('verified-specification-preview')
  await dialog.getByRole('button', { name: '确认保存' }).click()
  await expect(dialog).not.toBeVisible()
  const audit = page.locator('.takeover-audit li').filter({ hasText: '合成检验单 REF-H2-24' })
  await expect(audit).toContainText('补核规格 24 W')
  await expect(audit).toContainText('正式灯具 B')
  await audit.scrollIntoViewIfNeeded()
  await capture('audit-detail')

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: '导出 CSV' }).click()
  const csv = await download
  expect(csv.suggestedFilename()).toBe('历史商品明细.csv')
  const csvPath = path.join(output, 'history-products.csv')
  await csv.saveAs(csvPath)
  const exported = await readFile(csvPath, 'utf8')
  expect(exported).toContain('历史原文明细')
  expect(exported).toMatch(/A1,,旧分类,2(?:\.0+)?,pcs,50(?:\.0+)?,CNY,已关联,B/)

  await page.goto('/historical-orders', { waitUntil: 'domcontentloaded' })
  const analysis = page.locator('.analysis-card')
  const grouping = analysis.getByLabel('商品口径')
  const sales = analysis.locator('.analysis-detail-section').filter({
    has: page.getByRole('heading', { name: '历史销售明细', exact: true }),
  })
  await expect(sales.getByRole('heading', { name: '历史原文' })).toBeVisible()
  await grouping.selectOption('linked')
  await expect(sales.getByRole('heading', { name: '按关联 SKU 归集' })).toBeVisible()
  await sales.getByRole('heading', { name: '按关联 SKU 归集' }).scrollIntoViewIfNeeded()
  await capture('linked-analysis')

  const originalReport = url => url.pathname === '/api/reports/historical/' && url.searchParams.get('grouping') === 'original'
  let injectedFailures = 0
  await page.route(originalReport, route => {
    injectedFailures += 1
    return route.fulfill({ status: 503, json: { detail: '合成网络失败，等待重试' } })
  }, { times: 6 })
  const failedReport = page.waitForResponse(response => originalReport(new URL(response.url())))
  await grouping.selectOption('original')
  expect((await failedReport).status()).toBe(503)
  await expect(analysis.getByRole('alert')).toHaveText('服务器暂时不可用，请稍后重试。', { timeout: 20_000 })
  expect(injectedFailures).toBe(6)
  await analysis.getByRole('alert').scrollIntoViewIfNeeded()
  await capture('analysis-error')
  await analysis.getByRole('button', { name: '刷新分析' }).click()
  await expect(sales.getByRole('heading', { name: '历史原文' })).toBeVisible()
  await sales.getByRole('heading', { name: '历史原文' }).scrollIntoViewIfNeeded()
  await capture('original-analysis-recovered')
  await writeFile(path.join(output, 'chrome-checks.json'), JSON.stringify({
    chrome: browser.version(), viewport: page.viewportSize(), nativeZoom: `${nativeZoom}%`, effective,
    sourceSha: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
    backend: 'isolated SQLite and media root; six HTTP 503 responses simulate a failed analysis read through the app retry limit',
  }, null, 2))
})
