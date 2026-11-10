import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1280,height:720},deviceScaleFactor:1})
test('product form with four-level category tree',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 async function capture(stage){
  await page.evaluate(()=>document.fonts.ready)
  const info=await page.evaluate(()=>{const read=sel=>{const e=document.querySelector(sel);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {rect:{x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom},clientWidth:e.clientWidth,scrollWidth:e.scrollWidth,scrollLeft:e.scrollLeft,overflowX:s.overflowX}};return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,modal:read('.product-modal'),grid:read('.product-modal .form-grid'),picker:read('.product-modal .category-picker'),columns:read('.cascade-columns')}})
  const name=`ULR012-B-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  entries.push({evidence_id:name,surface_id:'P002',expanded_case_id:`ULR012-B-${stage}`,related_ulr:['ULR-012'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...info,role:'authenticated codex test superuser',data:'isolated synthetic 4-level long-name categories; unsaved blank product',steps:['open /products','open 新建产品','open primary category picker','expand 4-level category'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'product-tree-manifest.json'),JSON.stringify(entries,null,2))
 }
 await page.goto('/products',{waitUntil:'domcontentloaded'})
 await page.getByRole('button',{name:'新建产品'}).click()
 const modal=page.getByRole('dialog',{name:'新建产品'});await expect(modal).toBeVisible()
 await modal.locator('.category-select').first().click()
 await page.getByRole('button',{name:'合成商用建筑室内专业照明产品一级',exact:true}).click()
 await page.getByRole('button',{name:'合成办公室及展厅线性装饰照明二级',exact:true}).click()
 await page.getByRole('button',{name:'合成嵌入式吊装式组合灯具系列三级',exact:true}).click()
 await capture('4level-1280')
 await page.setViewportSize({width:1366,height:768});await capture('4level-1366')
 await page.getByRole('button',{name:'合成可调色温高显色灯具型号四级',exact:true}).click()
 await page.mouse.move(1000,600);await page.mouse.wheel(600,0);await page.waitForTimeout(400);await capture('selected-horizontal-wheel-1366')
 await modal.getByRole('button',{name:'新增',exact:true}).click()
 await modal.locator('.additional-row .category-select').click()
 await capture('additional-after-toggle-1366')
})
