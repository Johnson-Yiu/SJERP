import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { mkdtemp, readFile, realpath, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { basename, dirname, join } from 'node:path'
import { chromium, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'

const base = process.env.H1_BROWSER_ORIGIN || 'http://127.0.0.1:5398'
const config = Object.fromEntries((await readFile(process.env.H1_CREDENTIALS, 'utf8'))
  .split(/\r?\n/).filter(line => line && !line.startsWith('#'))
  .map(line => [line.slice(0, line.indexOf('=')), line.slice(line.indexOf('=') + 1)]))
const evidence = new URL('./', import.meta.url)
const browser = await chromium.launch({ channel: 'chrome' })
const observations = []
const layoutOnly = process.env.H1_LAYOUT_ONLY === '1'
const temp = await realpath(tmpdir())
const root = await mkdtemp(join(temp, 'sunjack-h1-chrome-'))

async function login(context) {
  const page = await context.newPage()
  await page.goto(base + '/login?next=/history-takeover', { waitUntil: 'domcontentloaded' })
  await page.getByLabel('账号', { exact: true }).fill(config.ERP_TEST_USERNAME)
  await page.getByLabel('密码', { exact: true }).fill(config.ERP_TEST_PASSWORD)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByText('历史商品关联', { exact: true })).toBeVisible()
  await page.getByText('历史商品关联', { exact: true }).click()
  await expect(page.getByRole('checkbox', { name: /A2灯/ })).toBeVisible()
  return page
}

async function preview(page, sku = 'B') {
  const dialog = page.getByRole('dialog')
  await page.getByRole('button', { name: /处理所选商品/ }).click()
  await expect(dialog.getByLabel('正式 SKU', { exact: true }).locator('option').filter({ hasText: '正式灯具 ' + sku })).toHaveCount(1)
  await dialog.getByLabel('正式 SKU', { exact: true }).selectOption({ label: `${sku} · 正式灯具 ${sku} · 24W · pcs` })
  await dialog.getByRole('button', { name: '生成预览' }).click()
  await expect(dialog.getByRole('region', { name: '关联预览' })).toBeVisible()
  return dialog
}

try {
  for (const width of [1366, 1440, 390]) {
    for (const scale of [1, 1.25]) {
      if (layoutOnly && scale === 1) continue
      const viewport = { width, height: 900 }
      const context = await chromium.launchPersistentContext(join(root, `profile-${width}-${scale}`), {
        channel: 'chrome', viewport,
      })
      try {
        const settings = context.pages()[0]
        await settings.setViewportSize({ width: 1440, height: 900 })
        await settings.goto('chrome://settings/appearance')
        const zoom = settings.getByRole('combobox', { name: /网页缩放|Page zoom/ })
        await zoom.selectOption({ label: `${scale * 100}%` })
        const page = await login(context)
        const effective = await page.evaluate(() => ({ width: innerWidth, dpr: devicePixelRatio }))
        assert.ok(Math.abs(effective.dpr - scale) < 0.01, JSON.stringify(effective))
        assert.ok(Math.abs(effective.width - width / scale) < 2, JSON.stringify(effective))
        if (layoutOnly) await page.getByRole('checkbox', { name: 'A', exact: true }).last().check()
        else await page.getByRole('checkbox', { name: 'A1', exact: true }).check()
        await page.getByRole('checkbox', { name: /A2灯/ }).check()
        const dialog = await preview(page)
        await expect(dialog.getByText('影响 2 条明细')).toBeVisible()
        await page.evaluate(() => window.scrollTo(0, 0))
        const box = await dialog.boundingBox()
        const footer = await dialog.getByRole('button', { name: '确认保存' }).boundingBox()
        assert.ok(footer.y + footer.height <= box.y + box.height)
        assert.ok(box.x >= 0 && box.x + box.width <= effective.width + 1)
        if (layoutOnly) {
          const session = await context.newCDPSession(page)
          try {
            const capture = await session.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
            await writeFile(new URL(`chrome-${width}-${scale * 100}-native.png`, evidence), Buffer.from(capture.data, 'base64'))
          } finally {
            await session.detach()
          }
        } else {
          await page.screenshot({ path: fileURLToPath(new URL(`chrome-${width}-${scale * 100}.png`, evidence)) })
        }
        observations.push({ width, browserZoom: scale, viewport, effective, dialog: box })
      } finally {
        await context.close()
      }
    }
  }

  if (layoutOnly) {
    console.log('Chrome native zoom viewport screenshots passed.')
  } else {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } })
  const page = await login(context)
  const competingContext = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const competing = await login(competingContext)
  await page.getByRole('checkbox', { name: 'A1', exact: true }).check()
  await page.getByRole('checkbox', { name: /A2灯/ }).check()
  const dialog = await preview(page)
  await competing.getByRole('checkbox', { name: 'A1', exact: true }).check()
  const competingDialog = await preview(competing, 'C')
  await competingDialog.getByRole('button', { name: '确认保存' }).click()
  await expect(competing.getByText('已更新 1 条历史商品。')).toBeVisible()
  await dialog.getByRole('button', { name: '确认保存' }).click()
  await expect(dialog.getByText(/关联未保存/)).toBeVisible()
  await page.screenshot({ path: fileURLToPath(new URL('chrome-390-conflict.png', evidence)) })
  await dialog.getByRole('button', { name: '关闭' }).click()
  await page.getByRole('button', { name: '查询', exact: true }).click()
  await page.getByRole('checkbox', { name: /A2灯/ }).check()
  await preview(page)
  await page.route('**/api/import/history-products/apply/', route => route.fulfill({
    status: 503, contentType: 'application/json', body: JSON.stringify({ detail: '暂时无法保存，请重试。' }),
  }), { times: 1 })
  await dialog.getByRole('button', { name: '确认保存' }).click()
  await expect(dialog.getByRole('alert')).toBeVisible()
  await page.screenshot({ path: fileURLToPath(new URL('chrome-390-retry.png', evidence)) })
  await dialog.getByRole('button', { name: '确认保存' }).click()
  await expect(page.getByText('已更新 1 条历史商品。')).toBeVisible()

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: '导出 CSV' }).click()
  const download = await downloadPromise
  const csvPath = new URL('history-products.csv', evidence)
  await download.saveAs(fileURLToPath(csvPath))
  const csv = await readFile(csvPath, 'utf8')
  assert.ok(csv.startsWith('\ufeff'))
  for (const value of ['原编码', 'A2灯', '正式灯具 B', '正式灯具 C', 'Legacy synthetic system', '待关联', '已关联']) assert.ok(csv.includes(value), value)
  await page.getByRole('link', { name: /B 正式灯具 B/ }).click()
  await expect(page).toHaveURL(/\/skus\?detail=\d+/)
  await page.goto(base + '/historical-orders')
  await page.getByLabel('商品口径').selectOption('linked')
  await expect(page.getByRole('cell', { name: 'B · 正式灯具 B', exact: true })).toBeVisible()
  await writeFile(new URL('chrome-checks.json', evidence), JSON.stringify({
    chrome: browser.version(), layouts: observations, conflict: 'HTTP 409 from competing real update',
    retry: 'synthetic HTTP 503 followed by successful real retry', csv: 'actual Chrome download parsed',
    navigation: 'SKU detail and historical linked analysis',
  }, null, 2))
  console.log('Chrome layout matrix, conflict, retry, download and navigation passed.')
  }
} finally {
  await browser.close()
  const resolved = await realpath(root)
  if (dirname(resolved) === temp && basename(resolved).startsWith('sunjack-h1-chrome-')) {
    await rm(resolved, { recursive: true, force: true })
  }
}
