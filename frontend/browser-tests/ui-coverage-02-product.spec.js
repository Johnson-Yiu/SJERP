import { test, expect } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('product detail on desktop workspaces',async({page,browser})=>{
  test.setTimeout(120000)
  const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
  await mkdir(path.join(root,'originals'),{recursive:true})
  await page.goto('/products',{waitUntil:'domcontentloaded'})
  const row=page.getByRole('row').filter({hasText:'WS-P001'})
  await expect(row).toBeVisible(); await row.click()
  const modal=page.locator('.product-detail-modal')
  await expect(modal).toBeVisible(); await expect(modal.getByText('Workspace Light',{exact:false}).first()).toBeAttached()
  await page.evaluate(()=>document.fonts.ready)
  const records=[]
  for(const [width,height] of [[1366,768],[1920,1080]]){
    await page.setViewportSize({width,height})
    await page.waitForFunction(() => document.querySelector('.product-detail-modal')?.getAnimations().every(a => a.playState !== 'running'))
    const measure=await page.evaluate(()=>{
      const read=selector=>{const e=document.querySelector(selector);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height,clientWidth:e.clientWidth,scrollWidth:e.scrollWidth,computedWidth:s.width,overflowX:s.overflowX,overflowY:s.overflowY}}
      return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,backdrop:read('.product-detail-backdrop'),article:read('.product-detail-modal')}
    })
    const name=`ULR003-B-${width}.png`,bytes=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
    records.push({evidence_id:name,surface_id:'P006',expanded_case_id:`ULR003-B-${width}`,related_ulr:['ULR-003'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...measure,role:'authenticated codex test superuser',object_reference:'WS-P001 / Workspace Light',data:'existing workspace-tabs synthetic fixture in isolated SQLite',steps:['open /products','click WS-P001','wait for product detail data','capture viewport'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(bytes).digest('hex'),pixels:{width:bytes.readUInt32BE(16),height:bytes.readUInt32BE(20)}})
    await writeFile(path.join(root,'product-manifest.json'),JSON.stringify(records,null,2))
  }
})
