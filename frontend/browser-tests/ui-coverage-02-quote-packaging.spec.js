import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('quote packaging failed save feedback',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 async function snap(stage){
  const info=await page.evaluate(()=>{const read=sel=>{const e=document.querySelector(sel);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {text:e.innerText.slice(0,500),rect:{x:r.x,y:r.y,width:r.width,height:r.height},visibility:s.visibility,display:s.display,zIndex:s.zIndex}};return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,parent:read('.quote-editor-modal'),child:read('.packaging-config-modal'),parentError:read('.quote-editor-modal .quote-message.error'),confirmation:read('.app-dialog-backdrop')}})
  const name=`ULR014-B-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  entries.push({evidence_id:name,surface_id:'S011',expanded_case_id:`ULR014-B-${stage}`,related_ulr:['ULR-014'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...info,role:'authenticated codex test superuser',object_reference:'ISS007-Q001 / ISS007-SKU001',data:'isolated synthetic quote and packaging template',simulated:'PUT packaging blocked before service, synthetic 503',capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'quote-packaging-manifest.json'),JSON.stringify(entries,null,2))
 }
 let intercepted=0
 await page.route('**/api/skus/*/packaging/',async route=>{if(route.request().method()==='PUT'){intercepted++;await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'隔离模拟包装保存失败'})})}else await route.continue()})
 await page.goto('/quotes',{waitUntil:'domcontentloaded'})
 await page.getByRole('row').filter({hasText:'ISS007-Q001'}).click()
 await page.getByRole('button',{name:'创建修订版',exact:true}).click()
 const parent=page.locator('.quote-editor-modal');await expect(parent).toBeVisible()
 await parent.getByRole('button',{name:'生成预计装箱方案'}).click()
 await parent.getByRole('button',{name:/补充默认包装/}).first().click()
 const child=page.locator('.packaging-config-modal');await expect(child).toBeVisible()
 await child.locator('select').selectOption({label:'合成包装模板'})
 await child.locator('input[type=number]').nth(0).fill('12');await child.locator('input[type=number]').nth(1).fill('1')
 const response=page.waitForResponse(r=>r.url().includes('/packaging/')&&r.request().method()==='PUT')
 await child.getByRole('button',{name:'保存默认包装'}).click();const res=await response
 await expect(parent.locator('.quote-message.error')).toBeAttached();await snap('failed-child')
 await writeFile(path.join(root,'quote-packaging-response.json'),JSON.stringify({status:res.status(),intercepted,body:await res.json(),note:'simulated in browser; request did not reach backend'},null,2))
 await child.getByRole('button',{name:'取消',exact:true}).click()
 const confirm=page.getByRole('button',{name:'放弃修改',exact:true})
 if(await confirm.count()) {try{await confirm.click({timeout:3000})}catch{await snap('close-confirm-blocked');return}}
 await expect(child).toHaveCount(0)
 await parent.locator('.quote-message.error').scrollIntoViewIfNeeded();await snap('parent-error')
})
