import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(scriptDir, '../../..')
const require = createRequire(resolve(repoRoot, 'frontend/browser-tests/iss007-followup-attachment-uat.mjs'))
const { chromium } = require('@playwright/test')
const evidenceDir = process.env.ISS007_UAT_EVIDENCE_DIR
const username = process.env.ISS007_UAT_USERNAME
const password = process.env.ISS007_UAT_PASSWORD
if (!evidenceDir || !username || !password) throw new Error('Missing isolated ISS007 UAT browser configuration.')

const browser = await chromium.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: false,
})
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
  await page.goto('http://127.0.0.1:8177/admin/login/', { waitUntil: 'domcontentloaded' })
  if (new URL(page.url()).pathname === '/admin/login/') {
    await page.locator('#id_username').fill(username)
    await page.locator('#id_password').fill(password)
    await page.locator('input[type="submit"]').click()
    await page.waitForURL(url => url.pathname.startsWith('/admin/'))
  }
  await page.goto('http://127.0.0.1:5279/follow-ups', { waitUntil: 'domcontentloaded' })
  const row = page.locator('tr').filter({ hasText: 'ISS007附件流程核验 2026-10-31' })
  await row.waitFor({ state: 'visible' })
  await row.getByRole('button', { name: '编辑跟进记录' }).click()
  const editor = page.locator('.crm-editor')
  await editor.waitFor({ state: 'visible' })
  const replacement = editor.locator('.follow-up-attachment-editor-item.saved').filter({ hasText: 'ISS007-delete-target-replacement.txt' })
  await replacement.waitFor({ state: 'visible' })
  await replacement.scrollIntoViewIfNeeded()
  const screenshot = path.join(evidenceDir, 'screenshots/mobile-replacement-visible-390x844.png')
  await page.screenshot({ path: screenshot, fullPage: false })
  const result = await page.evaluate(() => {
    const card = [...document.querySelectorAll('.follow-up-attachment-editor-item.saved')]
      .find(item => item.innerText.includes('ISS007-delete-target-replacement.txt'))
    const rect = card?.getBoundingClientRect()
    return {
      viewport: { width: innerWidth, height: innerHeight },
      documentScrollWidth: document.documentElement.scrollWidth,
      replacementVisible: Boolean(rect && rect.bottom > 0 && rect.top < innerHeight),
      replacementBounds: rect ? { top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right } : null,
      listedAttachments: [...document.querySelectorAll('.follow-up-attachment-editor-item.saved')].map(item => item.innerText.trim()),
    }
  })
  if (result.viewport.width !== 390 || result.documentScrollWidth > 390 || !result.replacementVisible) {
    throw new Error(`Replacement is not visibly framed at 390px: ${JSON.stringify(result)}`)
  }
  console.log(JSON.stringify({ screenshot, ...result }, null, 2))
} finally {
  await browser.close()
}
