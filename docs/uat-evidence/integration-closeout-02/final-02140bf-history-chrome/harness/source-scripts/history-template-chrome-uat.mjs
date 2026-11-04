import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { chromium } from '@playwright/test'
const origin = process.env.HISTORY_UAT_ORIGIN, dir = process.env.HISTORY_UAT_SESSION_DIR, evidence = process.env.HISTORY_UAT_EVIDENCE_DIR
if (!origin || !dir || !evidence || !/^http:\/\/127\.0\.0\.1:\d+$/.test(origin) || !path.basename(dir).startsWith('sunjack-history-operational-closeout-')) throw new Error('Marked loopback UAT is required')
const { sessionid, csrftoken } = JSON.parse(await readFile(path.join(dir, 'session.json'), 'utf8'))
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const context = await browser.newContext({ acceptDownloads: true })
await context.addCookies([{ name: 'sessionid', value: sessionid, url: origin, httpOnly: true, sameSite: 'Lax' }, { name: 'csrftoken', value: csrftoken, url: origin, sameSite: 'Lax' }])
try {
  const page = await context.newPage()
  await page.goto(`${origin}/history-takeover`, { waitUntil: 'networkidle' })
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载承接模板' }).click()
  await (await download).saveAs(path.join(evidence, 'history-takeover-template.xlsx'))
  console.log(`Chrome ${browser.version()}: downloaded actual takeover template from isolated API`)
} finally { await browser.close() }
