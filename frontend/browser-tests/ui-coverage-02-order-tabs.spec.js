import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('sales draft workbench tabs',async({page,browser})=>{
 test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true});await page.goto('/orders',{waitUntil:'networkidle'});await page.getByRole('row').filter({hasText:'WS-SO001'}).click();const detail=page.getByRole('dialog',{name:'订单工作台'});await expect(detail).toBeVisible()
 for(const [label,surface] of [['订单明细','S019'],['采购与发货','S020'],['回款','S021'],['装箱','S022'],['库存流水','S023'],['操作日志','S024']]){
  const button=detail.locator('.workbench-tabs button').filter({hasText:label});await button.click();await expect(button).toHaveClass(/active/);await page.waitForTimeout(250);const state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,visibleText:document.body.innerText.slice(0,4500)}));const id=`ORDER-${surface}-DRAFT-B-1366`,n=id+'.png',b=await page.screenshot({path:path.join(root,'originals',n)});entries.push({evidence_id:id,surface_id:surface,expanded_case_id:id,source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'isolated workspace fixture; draft WS-SO001 with one synthetic item',steps:['open WS-SO001 order workbench',`click ${label} tab`],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${n}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED',limitation:'draft initial tab only; no write operations'});await writeFile(path.join(root,'order-tabs-manifest.json'),JSON.stringify(entries,null,2))
 }
})
