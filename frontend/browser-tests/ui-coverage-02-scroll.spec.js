import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('workspace scroll with hidden packaging and SKU modals',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, records=[]
 await mkdir(path.join(root,'originals'),{recursive:true})
 const snapshot=async stage=>{
  const info=await page.evaluate(()=>{let e=document.elementFromPoint(900,650),chain=[];while(e){const s=getComputedStyle(e);chain.push({tag:e.tagName,className:typeof e.className==='string'?e.className:'',scrollTop:e.scrollTop,scrollHeight:e.scrollHeight,clientHeight:e.clientHeight,overflowY:s.overflowY});e=e.parentElement}return {scrollY,scrollHeight:document.documentElement.scrollHeight,clientHeight:document.documentElement.clientHeight,bodyOverflow:getComputedStyle(document.body).overflow,scrollChain:chain,hiddenModals:[...document.querySelectorAll('.workspace-pane[aria-hidden="true"] .modal-backdrop')].map(x=>({className:x.className,display:getComputedStyle(x.closest('.workspace-pane')).display})),route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale}})
  const name=`ULR006-B-v2-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  records.push({evidence_id:name,surface_id:'G002',expanded_case_id:`ULR006-B-${stage}`,related_ulr:['ULR-006'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...info,role:'authenticated codex test superuser',data:'workspace fixture; blank unsaved customer editor',simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'scroll-v2-manifest.json'),JSON.stringify(records,null,2))
 }
 const wheel=async stage=>{await page.mouse.move(900,650);await page.mouse.wheel(0,-4000);await page.waitForTimeout(300);await snapshot(`${stage}-before`);await page.mouse.wheel(0,550);await page.waitForTimeout(400);await snapshot(`${stage}-after`)}
 await page.goto('/customers',{waitUntil:'domcontentloaded'})
 await page.getByRole('button',{name:/新建客户/}).first().click()
 const customer=page.getByRole('tab',{name:/客户管理.*新建/}).first();await expect(customer).toBeVisible()
 await wheel('baseline')
 await page.getByRole('link',{name:'包装管理',exact:true}).click()
 await page.getByRole('button',{name:'新建模板'}).click()
 await expect(page.getByRole('dialog',{name:'新建包装模板'})).toBeVisible()
 await customer.click();await wheel('packaging-hidden')
 await page.getByRole('tab',{name:'包装管理',exact:true}).click()
 await page.getByRole('button',{name:'关闭模板表单'}).click()
 await customer.click();await wheel('packaging-closed')
 await page.getByRole('link',{name:'SKU 管理',exact:true}).click()
 const row=page.getByRole('row').filter({hasText:'WS-SKU001'});await expect(row).toBeVisible()
 await row.getByTitle('历史版本').click();await expect(page.getByRole('dialog',{name:'SKU 历史版本'})).toBeVisible()
 await customer.click();await wheel('sku-hidden')
 await page.getByRole('tab',{name:'SKU 管理',exact:true}).click()
 await page.getByRole('button',{name:'关闭历史版本'}).click()
 await customer.click();await wheel('sku-closed')
})
