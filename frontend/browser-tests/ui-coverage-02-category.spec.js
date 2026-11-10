import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1280,height:720},deviceScaleFactor:1})
test('inherited category source labels at compact desktop widths',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 async function snap(stage){
  await page.evaluate(()=>document.fonts.ready)
  const info=await page.evaluate(()=>{const b=document.querySelector('.source-badge.inherited'),cell=b?.closest('td'),next=cell?.nextElementSibling,sw=next?.querySelector('.rule-switch');const read=e=>{if(!e)return null;let r=e.getBoundingClientRect(),s=getComputedStyle(e);return {text:e.innerText,rect:{x:r.x,y:r.y,width:r.width,height:r.height,right:r.right},clientWidth:e.clientWidth,scrollWidth:e.scrollWidth,overflowX:s.overflowX,whiteSpace:s.whiteSpace}};return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,badge:read(b),cell:read(cell),nextCell:read(next),switch:read(sw)}})
  const name=`ULR011-B-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  entries.push({evidence_id:name,surface_id:'P036',expanded_case_id:`ULR011-B-${stage}`,related_ulr:['ULR-011'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...info,role:'authenticated codex test superuser',data:'isolated synthetic short/long inherited category fixture',steps:['open /categories','expand tree','select child','scroll attribute table into view'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'category-manifest.json'),JSON.stringify(entries,null,2))
 }
 await page.goto('/categories',{waitUntil:'domcontentloaded'})
 await page.getByRole('button',{name:'全部展开'}).click()
 await page.getByText('长来源子分类',{exact:true}).click()
 await expect(page.locator('.source-badge.inherited')).toBeVisible()
 await page.locator('.attribute-table').scrollIntoViewIfNeeded();await snap('long-1280')
 await page.setViewportSize({width:1366,height:768});await snap('long-1366')
 await page.getByText('短来源子分类',{exact:true}).click();await expect(page.locator('.source-badge.inherited')).toContainText('合成照明');await page.locator('.attribute-table').scrollIntoViewIfNeeded();await snap('short-1366')
})
