import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import path from 'node:path'
import {createHash} from 'node:crypto'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('inventory adjustment survives workspace switch',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 async function capture(stage){
  const data=await page.evaluate(()=>{
   const read=sel=>{const e=document.querySelector(sel);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {rect:{x:r.x,y:r.y,width:r.width,height:r.height},zIndex:s.zIndex,display:s.display,visibility:s.visibility,centerHit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML.slice(0,200)}}
   return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,modal:read('.inventory-movement-modal'),backdrop:read('.inventory-movement-backdrop'),title:read('.inventory-movement-modal .modal-head h3'),close:read('[aria-label="关闭手工库存流水"]'),activePane:document.querySelector('.workspace-pane[aria-hidden="false"]')?.getAttribute('aria-label'),bodyModalCount:document.querySelectorAll('body > .inventory-movement-backdrop').length}
  })
  const name=`ULR007-B-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  entries.push({evidence_id:name,surface_id:'G040',expanded_case_id:`ULR007-B-${stage}`,related_ulr:['ULR-007'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...data,role:'authenticated codex test superuser',data:'isolated workspace fixture; no save; selection outcome in inventory-selection.json',steps:['open customer list','open inventory ledger','open new adjustment','attempt SKU selection','switch customer tab'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'inventory-modal-manifest.json'),JSON.stringify(entries,null,2))
 }
 await page.goto('/customers',{waitUntil:'domcontentloaded'})
 await expect(page.getByRole('tab',{name:'客户管理',exact:true})).toBeVisible()
 await page.getByRole('link',{name:'库存流水',exact:true}).click()
 await page.getByRole('button',{name:'新建库存调整'}).click()
 const modal=page.getByRole('dialog',{name:'新建手工库存流水'});await expect(modal).toBeVisible()
 await page.evaluate(()=>document.fonts.ready)
 await capture('opened-before-select')
 const checkbox=modal.locator('label').filter({hasText:'WS-SKU001'}).locator('input[type=checkbox]')
 let selected=false
 try {await checkbox.check({timeout:3000});selected=true} catch {
  await modal.locator('.sku-picker-head input[type=search]').click({timeout:5000})
  for(let i=0;i<30;i++) {await page.keyboard.press('Tab');if(await page.evaluate(()=>document.activeElement?.closest('label')?.innerText.includes('WS-SKU001') && document.activeElement?.type==='checkbox')){await page.keyboard.press('Space');selected=await checkbox.isChecked();break}}
 }
 await writeFile(path.join(root,'inventory-selection.json'),JSON.stringify({selected,method:'pointer then ordinary keyboard navigation',note:'no forced click or component state changes'},null,2))
 await capture('opened-after-select')
 await page.getByRole('tab',{name:'客户管理',exact:true}).click()
 await capture('customer-active')
})
