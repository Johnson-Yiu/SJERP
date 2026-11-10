import { test, expect } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1920,height:1080},deviceScaleFactor:1})
test('supplier batch binding close confirmation from real product path',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, entries=[]
 await mkdir(path.join(root,'originals'),{recursive:true})
 async function snap(stage){
  await page.evaluate(()=>document.fonts.ready)
  const state=await page.evaluate(()=>{
   const read=sel=>{const e=document.querySelector(sel);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);const cx=r.x+r.width/2,cy=r.y+r.height/2;return {rect:{x:r.x,y:r.y,width:r.width,height:r.height},zIndex:s.zIndex,visible:s.visibility,centerHit:document.elementFromPoint(cx,cy)?.outerHTML.slice(0,250)}}
   return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,drawer:read('.binding-backdrop'),confirmation:read('.app-dialog-backdrop')}
  })
  const name=`ULR004-B-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  entries.push({evidence_id:name,surface_id:'P019',expanded_case_id:`ULR004-B-${stage}`,related_ulr:['ULR-004'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',object_reference:'WS-P001 / WS-SKU001 / Workspace Supplier',data:'existing workspace-tabs synthetic fixture in isolated SQLite',stage,simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'binding-manifest.json'),JSON.stringify(entries,null,2))
 }
 await page.goto('/products',{waitUntil:'domcontentloaded'})
 await page.getByRole('row').filter({hasText:'WS-P001'}).click()
 const modal=page.locator('.product-detail-modal')
 await expect(modal.getByText('Workspace Light',{exact:false}).first()).toBeAttached()
 await modal.locator('section').filter({hasText:'SKU 管理预览'}).getByRole('button',{name:'查看全部'}).click()
 await expect(page.getByLabel('选择 WS-SKU001')).toBeAttached()
 await snap('keyboard-sku-management')
 await page.getByPlaceholder('搜索 SKU 编码、中文名称或 Sales Model').click()
 let reached=false
 for(let i=0;i<30;i++){
  await page.keyboard.press('Tab')
  if(await page.evaluate(()=>document.activeElement?.getAttribute('aria-label')==='选择 WS-SKU001')){reached=true;break}
 }
 expect(reached,'SKU checkbox reachable through ordinary keyboard navigation').toBe(true)
 await page.keyboard.press('Space')
 await expect(page.getByLabel('选择 WS-SKU001')).toBeChecked()
 await snap('keyboard-selected')
 await page.getByRole('button',{name:'批量绑定供应商'}).click()
 const drawer=page.getByRole('dialog',{name:'批量绑定供应商'})
 await expect(drawer).toBeVisible()
 await drawer.getByRole('switch').check()
 await drawer.getByLabel('选择Workspace Supplier').check()
 await snap('dirty-before-close')
 await drawer.getByRole('button',{name:'关闭',exact:true}).click()
 await expect(page.getByText('未保存修改',{exact:false}).first()).toBeAttached()
 await snap('after-close')
 let result
 try {
  await page.getByRole('button',{name:'继续编辑',exact:true}).click({timeout:3000})
  result={action:'normal click 继续编辑',outcome:'clicked'}
 } catch(error) {
  result={action:'normal click 继续编辑',outcome:'blocked',error:String(error)}
 }
 await writeFile(path.join(root,'binding-click-result.json'),JSON.stringify(result,null,2))
 await snap('after-click-attempt')
})
