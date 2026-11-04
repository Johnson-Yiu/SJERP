import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium, expect } from 'file:///D:/Codex%E9%A1%B9%E7%9B%AE/%E6%A3%AE%E7%88%B5%E7%85%A7%E6%98%8E%E7%AE%A1%E7%90%86%E7%B3%BB%E7%BB%9F/.worktrees/r1-prelaunch-consolidation-20261104/.tmp/final-integrated-447d/frontend/node_modules/@playwright/test/index.mjs'
const origin = process.env.HISTORY_UAT_ORIGIN, dir = process.env.HISTORY_UAT_SESSION_DIR, evidence = process.env.HISTORY_UAT_EVIDENCE_DIR
if (!origin || !dir || !evidence || !/^http:\/\/127\.0\.0\.1:\d+$/.test(origin) || !path.basename(dir).startsWith('sunjack-history-operational-closeout-')) throw new Error('Marked loopback UAT is required')
const { sessionid, csrftoken } = JSON.parse(await readFile(path.join(dir, 'session.json'), 'utf8'))
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
await context.addCookies([{ name: 'sessionid', value: sessionid, url: origin, httpOnly: true, sameSite: 'Lax' }, { name: 'csrftoken', value: csrftoken, url: origin, sameSite: 'Lax' }])
const page = await context.newPage(), errors = []
page.on('pageerror', e => errors.push(e.message))
try {
  await page.goto(`${origin}/inventory-movements`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '新建库存调整', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '新建手工库存流水' })
  await dialog.locator('.sku-picker-options label').filter({ hasText: 'SKU-000001' }).locator('input').check()
  await dialog.getByLabel('SKU-000001 仓库类型').selectOption('自有仓')
  await dialog.getByLabel('SKU-000001 仓库', { exact: true }).fill('SYN-WH-01')
  await dialog.getByLabel('SKU-000001 批次或货位').fill('LOT-HT-01')
  await expect(dialog.getByLabel('SKU-000001 批次或货位')).toHaveValue('LOT-HT-01')
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport); await page.waitForTimeout(700)
    await dialog.getByLabel('SKU-000001 批次或货位').scrollIntoViewIfNeeded()
    await page.screenshot({ path: path.join(evidence, `inventory-location-${viewport.width}.png`) })
  }
  if (errors.length) throw new Error(errors.join('; '))
  await writeFile(path.join(evidence, 'inventory-location-chrome.json'), JSON.stringify({ chrome: browser.version(), scenario: 'synthetic manual movement input only; no save', widths: [1440, 390], errors }, null, 2) + '\n')
  console.log('Chrome manual inventory location input verified; no inventory movement submitted')
} finally { await browser.close() }
