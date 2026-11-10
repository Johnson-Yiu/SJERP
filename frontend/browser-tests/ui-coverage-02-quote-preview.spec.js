import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import path from 'node:path'
import {createHash} from 'node:crypto'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('saved quote PI preview geometry',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,records=[];await mkdir(path.join(root,'originals'),{recursive:true})
 async function capture(stage,status){
  await page.evaluate(()=>document.fonts.ready)
  const info=await page.evaluate(()=>{
   const read=sel=>{const e=document.querySelector(sel);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {rect:{x:r.x,y:r.y,width:r.width,height:r.height},top:s.top,left:s.left,maxHeight:s.maxHeight,overflow:s.overflow,zIndex:s.zIndex,centerHit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML.slice(0,200)}}
   return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,parent:read('.detail-backdrop'),backdrop:read('.quote-preview-backdrop'),preview:read('.quote-preview-modal'),close:read('[aria-label="关闭预览"]'),iframe:read('iframe[title="已保存 PI"]')}
  })
  const name=`ULR008-B-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  records.push({evidence_id:name,surface_id:'S005',expanded_case_id:`ULR008-B-${stage}`,related_ulr:['ULR-008'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...info,role:'authenticated codex test superuser',object_reference:'ISS007-Q001',data:'existing isolated ISS-007 synthetic quote fixture',steps:['open /quotes','open ISS007-Q001','click 预览 PI','wait for response and fonts'],pi_data_http_status:status,simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'quote-preview-manifest.json'),JSON.stringify(records,null,2))
 }
 await page.goto('/quotes',{waitUntil:'domcontentloaded'})
 await page.getByRole('row').filter({hasText:'ISS007-Q001'}).click()
 const button=page.getByRole('button',{name:'预览 PI',exact:true}).first();await expect(button).toBeVisible()
 const responsePromise=page.waitForResponse(r=>r.url().includes('/pi-data/') && r.request().method()==='GET')
 await button.click();const response=await responsePromise
 if(response.ok()){
  await expect(page.getByRole('dialog',{name:'PI 预览'})).toBeVisible()
  await page.locator('iframe[title="已保存 PI"]').waitFor({state:'attached'})
  await page.waitForFunction(()=>{const d=document.querySelector('iframe[title="已保存 PI"]')?.contentDocument;return d?.readyState==='complete' && [...d.images].every(x=>x.complete)})
  await capture('1366',response.status());await page.setViewportSize({width:1920,height:1080});await capture('1920',response.status())
 }else await capture('preview-failed',response.status())
})
