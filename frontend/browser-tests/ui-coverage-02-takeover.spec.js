import { test, expect } from '@playwright/test'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { createHash } from 'node:crypto'
test.use({ channel: 'chrome', viewport: { width: 1366, height: 768 }, deviceScaleFactor: 1 })
test('capture takeover initial state', async ({ page, browser }) => {
  test.setTimeout(120000)
  const root = process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
  await mkdir(path.join(root, 'originals'), {recursive:true})
  await page.goto('/history-takeover', {waitUntil:'networkidle'})
  await expect(page.getByText('历史资料承接', {exact:false}).first()).toBeVisible()
  await page.evaluate(() => document.fonts.ready)
  const evidence=[]
  for (const [width,height] of [[1366,768],[1920,1080]]) {
    await page.setViewportSize({width,height})
    const data = await page.evaluate(() => ({route:location.pathname, viewport:{width:innerWidth,height:innerHeight}, dpr:devicePixelRatio, zoom:visualViewport.scale, styles:Object.fromEntries(['.takeover-columns','.takeover-form-grid','.takeover-actions'].map(selector => { const el=document.querySelector(selector); if(!el) return [selector,null]; const s=getComputedStyle(el); return [selector,{display:s.display,gridTemplateColumns:s.gridTemplateColumns,gap:s.gap}] }))}))
    const name=`ULR001-B-${width}.png`, file=path.join(root,'originals',name)
    await page.screenshot({path:file,fullPage:false})
    const bytes=await readFile(file)
    evidence.push({evidence_id:name,surface_id:'F037',expanded_case_id:`ULR001-B-initial-${width}`,related_ulr:['ULR-001'],state:'empty isolated takeover initial',source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...data,role:'authenticated codex test superuser',data:'fresh isolated SQLite; no takeover records',steps:['navigate directly to /history-takeover','wait for network idle and fonts','capture viewport'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(bytes).digest('hex'),pixels:{width:bytes.readUInt32BE(16),height:bytes.readUInt32BE(20)}})
  }
  await writeFile(path.join(root,'takeover-manifest.json'),JSON.stringify(evidence,null,2))
})
