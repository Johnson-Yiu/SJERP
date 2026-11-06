import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium, expect } from '@playwright/test'

const origin = process.env.HISTORY_UAT_ORIGIN || 'http://127.0.0.1:5195'
const sessionFile = process.env.HISTORY_UAT_SESSION_FILE
const evidenceDir = process.env.HISTORY_UAT_EVIDENCE_DIR
const applicationId = process.env.HISTORY_UAT_APPLICATION_ID
if (!sessionFile || !evidenceDir || !applicationId) throw new Error('Missing disposable UAT session, evidence directory, or application ID.')

const { sessionid, csrftoken } = JSON.parse(await readFile(sessionFile, 'utf8'))
await mkdir(evidenceDir, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const failures = []
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true })
await context.addCookies([
  { name: 'sessionid', value: sessionid, url: origin, httpOnly: true, sameSite: 'Lax' },
  { name: 'csrftoken', value: csrftoken, url: origin, sameSite: 'Lax' },
])
const page = await context.newPage()
page.on('pageerror', error => failures.push(`pageerror: ${error.message}`))
page.on('console', message => {
  if (message.type() === 'error' && !message.text().includes('404 (Not Found)')) failures.push(`console: ${message.text()}`)
})
page.on('response', response => {
  if (response.status() < 400) return
  const pathname = new URL(response.url()).pathname
  if (pathname !== '/favicon.ico') failures.push(`HTTP ${response.status()} ${response.url()}`)
})

try {
  await page.goto(`${origin}/history-takeover`, { waitUntil: 'networkidle' })
  await expect(page.getByRole('heading', { level: 2, name: '历史资料承接' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 3, name: 'synthetic-history-uAT.xlsx' })).toBeVisible()
  await expect(page.getByText('Synthetic browser UAT')).toBeVisible()

  const screenshots = []
  const templateDownload = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载承接模板' }).click()
  const template = await templateDownload
  await template.saveAs(path.join(evidenceDir, 'history-takeover-template-v1.xlsx'))
  if (!await page.getByRole('heading', { name: '执行结果' }).count()) {
    await page.screenshot({ path: path.join(evidenceDir, 'history-takeover-desktop-before-review.png') })
    screenshots.push('history-takeover-desktop-before-review.png')
    await page.getByLabel('审核依据').fill('合成验收：核对隔离工作簿、合成主体和来源凭证引用。')
    await page.getByLabel('已依据原始凭证核实所有待核实项').check()
    await page.getByRole('button', { name: '批准', exact: true }).click()
    await expect(page.getByRole('button', { name: '承接', exact: true })).toBeVisible()
    page.once('dialog', dialog => dialog.accept())
    await page.getByRole('button', { name: '承接', exact: true }).click()
  }
  await expect(page.getByRole('heading', { name: '执行结果' })).toBeVisible({ timeout: 15000 })
  await expect(page.getByText(/正式资金、库存流水、履约记录、采购成本分配均为 0/)).toBeVisible()
  await page.locator('.takeover-execution').scrollIntoViewIfNeeded()
  await page.screenshot({ path: path.join(evidenceDir, 'history-takeover-desktop-executed.png') })
  screenshots.push('history-takeover-desktop-executed.png')

  await page.setViewportSize({ width: 390, height: 844 })
  await page.locator('.takeover-execution').scrollIntoViewIfNeeded()
  await page.waitForTimeout(300)
  const mobileWidth = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }))
  await page.screenshot({ path: path.join(evidenceDir, 'history-takeover-390px-executed.png') })
  screenshots.push('history-takeover-390px-executed.png')
  if (mobileWidth.document > mobileWidth.viewport || mobileWidth.body > mobileWidth.viewport) {
    failures.push(`horizontal overflow at 390px: ${JSON.stringify(mobileWidth)}`)
  }

  const report = {
    browser: `Google Chrome ${browser.version()}`,
    origin,
    applicationId,
    viewports: [{ width: 1440, height: 1000 }, { width: 390, height: 844 }],
    template: 'history-takeover-template-v1.xlsx',
    screenshots,
    mobileWidth,
    failures,
  }
  await writeFile(path.join(evidenceDir, 'chrome-run.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8')
  if (failures.length) throw new Error(`Chrome UAT reported failures: ${failures.join('; ')}`)
  console.log(JSON.stringify(report, null, 2))
} finally {
  await browser.close()
}
