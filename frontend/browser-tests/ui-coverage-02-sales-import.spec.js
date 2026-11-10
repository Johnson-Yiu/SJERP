import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('long import failure feedback location',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 async function snap(stage){
  const info=await page.evaluate(()=>{const e=document.querySelector('.error-result[role="alert"]'),r=e?.getBoundingClientRect();return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,scrollY,documentHeight:document.documentElement.scrollHeight,error:r?{text:e.innerText,x:r.x,y:r.y,width:r.width,height:r.height}:null,rows:document.querySelectorAll('.order-result-table tbody tr').length}})
  const name=`ULR015-B-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  entries.push({evidence_id:name,surface_id:'F032',expanded_case_id:`ULR015-B-${stage}`,related_ulr:['ULR-015'],source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...info,role:'authenticated codex test superuser',data:'150 synthetic orders, isolated SQLite',simulated:'execute intercepted before service, HTTP 503',capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'sales-import-manifest.json'),JSON.stringify(entries,null,2))
 }
 let intercepted=0
 await page.route('**/api/import/orders/execute/',async route=>{intercepted++;await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'隔离模拟提交结果未知'})})})
 await page.goto('/import',{waitUntil:'domcontentloaded'})
 await page.getByRole('tab',{name:'销售订单',exact:true}).click()
 await page.locator('input[type=file][accept*=".xlsx"]').setInputFiles(path.join(process.env.ISOLATED_TEST_ROOT,'ui-coverage-long-orders.xlsx'))
 await page.getByRole('button',{name:'预览并校验',exact:true}).click()
 const execute=page.getByRole('button',{name:'确认导入 150 张草稿',exact:true});await expect(execute).toBeVisible({timeout:30000})
 await execute.scrollIntoViewIfNeeded();await snap('before-submit')
 await execute.click();await page.getByTestId('dialog-confirm').click()
 await expect(page.getByRole('alert').filter({hasText:'提交结果待核对'})).toBeAttached()
 await snap('failure-bottom')
 await writeFile(path.join(root,'sales-import-intercept.json'),JSON.stringify({intercepted,status:503,note:'request fulfilled by browser before reaching backend'},null,2))
 await page.getByRole('alert').filter({hasText:'提交结果待核对'}).scrollIntoViewIfNeeded();await snap('failure-top')
})
