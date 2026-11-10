import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import path from 'node:path'
import {createHash} from 'node:crypto'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('purchase receipt dialog viewport bounds',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 async function capture(stage){
  await page.evaluate(()=>document.fonts.ready)
  const info=await page.evaluate(()=>{
   const read=sel=>{const e=document.querySelector(sel);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {rect:{x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom},clientHeight:e.clientHeight,scrollHeight:e.scrollHeight,scrollTop:e.scrollTop,maxHeight:s.maxHeight,overflow:s.overflow,zIndex:s.zIndex,centerHit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML.slice(0,200)}}
   return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,workspaceTop:getComputedStyle(document.documentElement).getPropertyValue('--workspace-top'),mask:read('.receipt-mask'),dialog:read('.goods-receipt-dialog'),footer:read('.goods-receipt-dialog footer')}
  })
  const name=`ULR009-B-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  entries.push({evidence_id:name,surface_id:'S040',expanded_case_id:`ULR009-B-${stage}`,related_ulr:['ULR-009'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...info,role:'authenticated codex test superuser',data:'existing core-workspace synthetic formal purchase and pending item; no receipt submitted',steps:['open /purchase-orders','open isolated UXPO purchase','select 收货','open 验货入库','expand location and scroll'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'receipt-manifest.json'),JSON.stringify(entries,null,2))
 }
 await page.goto('/purchase-orders',{waitUntil:'domcontentloaded'})
 await page.getByRole('row').filter({hasText:'UXPO'}).first().click()
 await page.getByRole('button',{name:'收货',exact:true}).click()
 await page.getByRole('button',{name:'验货入库',exact:true}).first().click()
 const dialog=page.getByRole('dialog',{name:'验货合格入库'});await expect(dialog).toBeVisible()
 await capture('1366-top')
 await dialog.getByLabel('指定入库仓库和批次').check({timeout:6000})
 await page.mouse.move(900,600);await page.mouse.wheel(0,3000);await page.waitForTimeout(400);await capture('1366-location-bottom')
 await page.setViewportSize({width:1920,height:1080});await page.mouse.move(1200,700);await page.mouse.wheel(0,3000);await page.waitForTimeout(400);await capture('1920-location-bottom')
})
