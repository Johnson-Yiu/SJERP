import { test, expect } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'

test.use({ channel: 'chrome', viewport: { width: 1366, height: 768 }, deviceScaleFactor: 1 })

test('capture historical preflight and first cash list load', async ({ page, browser }) => {
  test.setTimeout(120000)
  const root = process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
  const originals = path.join(root, 'originals')
  await mkdir(originals, { recursive: true })
  const manifest = []
  const capture = async (name, surface, state, simulated) => {
    await page.evaluate(() => document.fonts.ready)
    const meta = await page.evaluate(() => ({ viewport_actual: { width: innerWidth, height: innerHeight }, dpr: devicePixelRatio, zoom: visualViewport.scale, route: location.pathname + location.search }))
    const file = path.join(originals, name)
    await page.screenshot({ path: file, fullPage: false })
    const bytes = await readFile(file)
    manifest.push({ evidence_id: name, surface_id: surface, state, source_branch: 'codex/first-release-independent-review-02', source_sha: 'c90cacaa99a468d92dd61c41437834c5d8acb094', browser_version: browser.version(), ...meta, role: 'authenticated codex test superuser; development_superadmin=false; RBAC enforcement=false in isolated DB', data: 'new isolated SQLite database', simulated, capture_time_utc: new Date().toISOString(), file: `originals/${name}`, sha256: createHash('sha256').update(bytes).digest('hex'), pixels: {width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20)} })
  }
  await page.goto('/history-preflight', {waitUntil:'networkidle'})
  await capture('F035-B-1366.png', 'F035', 'history preflight initial', false)
  await page.setViewportSize({width:1920,height:1080})
  await capture('F035-B-1920.png', 'F035', 'history preflight initial', false)
  await page.setViewportSize({width:1366,height:768})
  let release
  const gate = new Promise(resolve => { release = resolve })
  let requestSeen
  const seen = new Promise(resolve => { requestSeen = resolve })
  await page.route('**/api/rmb-cash-events/**', async route => { requestSeen(); await gate; await route.continue() })
  await page.goto('/rmb-cash-events', {waitUntil:'domcontentloaded'})
  await seen
  await expect(page.getByText('银行资金记录', {exact:false}).first()).toBeVisible()
  await capture('ULR018-B-1366-pending.png', 'F021', 'first GET pending', true)
  release()
  await page.waitForResponse(r => r.url().includes('/api/rmb-cash-events/') && r.request().method() === 'GET')
  await page.waitForLoadState('networkidle')
  await capture('ULR018-B-1366-loaded.png', 'F021', 'first GET complete', true)
  await writeFile(path.join(root, 'initial-manifest.json'), JSON.stringify(manifest, null, 2))
})
