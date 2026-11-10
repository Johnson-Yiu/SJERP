import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',deviceScaleFactor:1})
test('customer empty database initial state',async({page,browser})=>{
 test.setTimeout(90000); const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 for(const size of [{width:1366,height:768},{width:1920,height:1080}]){
  await page.setViewportSize(size);const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/customers/'&&r.request().method()==='GET');await page.goto('/customers',{waitUntil:'networkidle'});const response=await responsePromise;expect(response.status()).toBe(200);const body=await response.json();const data=Array.isArray(body)?body:body.results;expect(data).toEqual([]);await expect(page.getByText('暂无客户',{exact:true})).toBeVisible();await page.evaluate(()=>document.fonts.ready)
  const state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,scrollY,visibleText:document.body.innerText.slice(0,4000)}));const id=`CUSTOMER-EMPTY-B-${size.width}`,name=id+'.png',b=await page.screenshot({path:path.join(root,'originals',name)});entries.push({evidence_id:id,surface_id:'G022',expanded_case_id:id,source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'fresh isolated migrated database; no customer fixture; list response 200 with zero rows',steps:['open customer list in isolated database','verify empty customer response and empty-state text','capture viewport'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED'});await writeFile(path.join(root,'customer-empty-manifest.json'),JSON.stringify(entries,null,2))
 }
})
