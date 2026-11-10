import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('customer related order selected status and intercepted payload',async({page,browser})=>{
 test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT;await mkdir(path.join(root,'originals'),{recursive:true})
 let payload=null
 await page.route('**/api/orders/',async route=>{if(route.request().method()==='POST'){payload=route.request().postDataJSON();await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"隔离拦截，不创建订单"}'})}else await route.continue()})
 await page.goto('/customers',{waitUntil:'domcontentloaded'});await page.getByRole('row').filter({hasText:'Workspace Alpha'}).click()
 await page.getByRole('button',{name:/订单记录/}).first().click();await page.getByRole('button',{name:/新增订单/}).first().click()
 const modal=page.locator('.related-create-modal');await expect(modal).toBeVisible()
 const status=modal.locator('.field').filter({hasText:'状态'}).locator('select');await status.selectOption('confirmed')
 await status.scrollIntoViewIfNeeded();await page.evaluate(()=>document.fonts.ready)
 const statusTime=new Date().toISOString(),statusBytes=await page.screenshot({path:path.join(root,'originals','ULR019-B-status.png'),fullPage:false})
 await writeFile(path.join(root,'related-order-status-manifest.json'),JSON.stringify({evidence_id:'ULR019-B-status.png',surface_id:'S017',expanded_case_id:'ULR019-B-status',related_ulr:['ULR-019'],source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',source_branch:'codex/first-release-independent-review-02',browser_version:browser.version(),route:new URL(page.url()).pathname+new URL(page.url()).search,viewport_actual:{width:1366,height:768},dpr:1,zoom:1,role:'authenticated codex test superuser',fixture:'Workspace Alpha / WS-SKU001',steps:['客户列表打开 Workspace Alpha','订单记录','新增订单','状态选择已确认'],selected_status:await status.inputValue(),capture_time_utc:statusTime,simulated:false,file:'originals/ULR019-B-status.png',sha256:createHash('sha256').update(statusBytes).digest('hex'),pixels:{width:statusBytes.readUInt32BE(16),height:statusBytes.readUInt32BE(20)}},null,2))
 await modal.locator('.sku-picker-options label').filter({hasText:'WS-SKU001'}).locator('input').check()
 const shot=path.join(root,'originals','ULR019-B-selected.png'),b=await page.screenshot({path:shot,fullPage:false})
 const response=page.waitForResponse(r=>r.url().endsWith('/api/orders/')&&r.request().method()==='POST')
 await modal.getByRole('button',{name:'保存',exact:true}).click();const res=await response
 await writeFile(path.join(root,'related-order-result.json'),JSON.stringify({selected_status:'confirmed',request_payload:payload,status:res.status(),intercepted_before_service:true},null,2))
 await writeFile(path.join(root,'related-order-manifest.json'),JSON.stringify([{evidence_id:'ULR019-B-selected.png',surface_id:'S017',expanded_case_id:'ULR019-B-selected',related_ulr:['ULR-019'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),route:page.url(),viewport_actual:{width:1366,height:768},dpr:1,zoom:1,role:'authenticated codex test superuser',data:'isolated Workspace Alpha and WS-SKU001',simulated:'POST intercepted before service',capture_time_utc:new Date().toISOString(),file:'originals/ULR019-B-selected.png',sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}}],null,2))
 const other=await page.context().newPage();await other.goto('/orders',{waitUntil:'domcontentloaded'});await other.getByRole('button',{name:/新建订单/}).first().click();await expect(other.locator('input[value=草稿][readonly]')).toBeVisible();await other.evaluate(()=>document.fonts.ready)
 const at=new Date().toISOString(),c=await other.screenshot({path:path.join(root,'originals','ULR019-B-normal.png'),fullPage:false})
 await writeFile(path.join(root,'related-order-normal-manifest.json'),JSON.stringify({evidence_id:'ULR019-B-normal.png',surface_id:'S016',expanded_case_id:'ULR019-B-normal',related_ulr:['ULR-019'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),route:new URL(other.url()).pathname+new URL(other.url()).search,viewport_actual:{width:1366,height:768},dpr:1,zoom:1,role:'authenticated codex test superuser',fixture:'isolated workspace fixture',steps:['订单管理','新建订单'],capture_time_utc:at,simulated:false,file:'originals/ULR019-B-normal.png',sha256:createHash('sha256').update(c).digest('hex'),pixels:{width:c.readUInt32BE(16),height:c.readUInt32BE(20)}},null,2));await other.close()
})
