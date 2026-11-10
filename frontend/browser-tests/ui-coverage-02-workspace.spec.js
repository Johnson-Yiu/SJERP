import { test, expect } from '@playwright/test'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { createHash } from 'node:crypto'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('customer create followed by products navigation', async ({page,browser}) => {
  test.setTimeout(120000)
  const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
  const variant=process.env.UI_COVERAGE_VARIANT
  const sha=variant==='A'?'c978758f37db8b8acf5e751fc7aa836287163a6b':'c90cacaa99a468d92dd61c41437834c5d8acb094'
  if(!['A','B'].includes(variant)) throw new Error('UI_COVERAGE_VARIANT must be A or B')
  await mkdir(path.join(root,'originals'),{recursive:true})
  const entries=[]
  async function snap(stage){
    await page.evaluate(()=>document.fonts.ready)
    const state=await page.evaluate(()=>({route:location.pathname+location.search, viewport:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,workspace_tabs:document.querySelectorAll('.workspace-tab').length,sidebar_text:document.querySelector('.sidebar nav')?.innerText || ''}))
    const name=`ULR002-${variant}-${stage}.png`, bytes=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
    entries.push({evidence_id:name,surface_id:'G001',expanded_case_id:`ULR002-${variant}-${stage}`,related_ulr:['ULR-002'],source_branch:variant==='A'?'codex/finance-receipt-optimization-02':'codex/first-release-independent-review-02',source_sha:sha,browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'fresh isolated SQLite; blank unsaved form',simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(bytes).digest('hex'),pixels:{width:bytes.readUInt32BE(16),height:bytes.readUInt32BE(20)}})
    await writeFile(path.join(root,`workspace-${variant}-manifest.json`),JSON.stringify(entries,null,2))
  }
  await page.goto('/customers',{waitUntil:'networkidle'})
  await page.getByRole('button',{name:/新建客户/}).first().click()
  await snap('customer-create')
  await page.getByRole('link',{name:'产品管理',exact:true}).first().click()
  await expect(page.getByText('产品管理',{exact:false}).first()).toBeVisible()
  await page.waitForLoadState('networkidle')
  await snap('products')
})
