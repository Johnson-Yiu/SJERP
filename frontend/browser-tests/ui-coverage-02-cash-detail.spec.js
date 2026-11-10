import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('confirmed cash event detail against workspace tabs',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 await page.goto('/rmb-cash-events',{waitUntil:'domcontentloaded'})
 const row=page.getByRole('row').filter({hasText:'CSV2-09-0'});await expect(row).toBeVisible();await row.getByRole('button',{name:'查看详情'}).click()
 await expect(page.locator('.cash-detail-panel')).toBeVisible();await page.evaluate(()=>document.fonts.ready)
 for(const [width,height] of [[1366,768],[1920,1080]]){
  await page.setViewportSize({width,height})
  const info=await page.evaluate(()=>{
   const read=sel=>{const e=document.querySelector(sel);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {rect:{x:r.x,y:r.y,width:r.width,height:r.height},zIndex:s.zIndex,centerHit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML.slice(0,240)}}
   return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,detail:read('.cash-detail-panel'),title:read('#cash-detail-title'),close:read('[aria-label="关闭资金详情"]'),workspaceBar:read('.workspace-bar')}
  })
  const name=`ULR010-B-${width}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  entries.push({evidence_id:name,surface_id:'F022',expanded_case_id:`ULR010-B-${width}`,related_ulr:['ULR-010'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...info,role:'authenticated codex test superuser',object_reference:'CSV2-09-0, confirmed',data:'existing export-stability API synthetic fixture adapted to isolated codex authentication',steps:['open /rmb-cash-events','open confirmed CSV2-09-0','capture viewport'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'cash-detail-manifest.json'),JSON.stringify(entries,null,2))
 }
})
