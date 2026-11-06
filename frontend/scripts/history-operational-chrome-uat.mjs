import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium, expect } from '@playwright/test'

const origin = process.env.HISTORY_UAT_ORIGIN
const sessionFile = process.env.HISTORY_UAT_SESSION_FILE
const evidenceDir = process.env.HISTORY_UAT_EVIDENCE_DIR
if (!origin || !sessionFile || !evidenceDir) throw new Error('Isolated origin, session and evidence path are required')
const { sessionid, csrftoken } = JSON.parse(await readFile(sessionFile, 'utf8'))
await mkdir(evidenceDir, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
await context.addCookies([{ name: 'sessionid', value: sessionid, url: origin, httpOnly: true, sameSite: 'Lax' },
  { name: 'csrftoken', value: csrftoken, url: origin, sameSite: 'Lax' }])
const page = await context.newPage()
const errors = []
page.on('pageerror', e => errors.push(e.message))
try {
  await page.goto(`${origin}/history-takeover`, { waitUntil: 'networkidle' })
  await expect(page.getByRole('heading', { name: 'synthetic-history-uAT.xlsx' })).toBeVisible()
  if (!await page.getByRole('heading', { name: '执行结果' }).count()) {
    await page.getByLabel('审核依据').fill('合成资料：核对来源、依赖与凭证')
    await page.getByLabel('已依据原始凭证核实所有待核实项').check()
    await page.getByRole('button', { name: '批准', exact: true }).click()
    await expect(page.getByRole('button', { name: '承接', exact: true })).toBeVisible()
    page.once('dialog', dialog => dialog.accept())
    await page.getByRole('button', { name: '承接', exact: true }).click()
  }
  await expect(page.getByRole('heading', { name: '执行结果' })).toBeVisible()
  for (const name of ['历史资金接续', '库存盘点基准', '未结余额与剩余业务']) {
    await page.getByText(name, { exact: true }).click()
  }
  await page.getByRole('button', { name: '加载资金来源、账户和凭证' }).click()
  await expect(page.getByText('TX-SO-1', { exact: false }).first()).toBeVisible()
  await page.getByRole('button', { name: '加载盘点来源' }).click()
  await expect(page.getByText('SYN-WH-01', { exact: false }).first()).toBeVisible()
  await page.getByRole('button', { name: '加载合同与未结来源' }).click()
  await expect(page.getByText('PLAN-SO-1', { exact: false }).first()).toBeVisible()
  const screenshots = []
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport)
    await page.waitForTimeout(700)
    await page.locator('.takeover-execution').scrollIntoViewIfNeeded()
    const dimensions = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }))
    if (dimensions.document > dimensions.viewport) errors.push(`horizontal overflow: ${JSON.stringify(dimensions)}`)
    const name = `history-operational-${viewport.width}.png`
    await page.screenshot({ path: path.join(evidenceDir, name), fullPage: true })
    screenshots.push({ name, viewport, dimensions })
  }
  const result = { chrome: browser.version(), data: 'disposable SQLite and synthetic workbook', screenshots, errors }
  await writeFile(path.join(evidenceDir, 'chrome-run.json'), JSON.stringify(result, null, 2) + '\n')
  if (errors.length) throw new Error(errors.join('; '))
  console.log(JSON.stringify(result, null, 2))
} finally { await browser.close() }
