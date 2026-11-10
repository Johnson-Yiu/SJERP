import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',deviceScaleFactor:1})
test('direct access status page structures',async({page,browser})=>{
 test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 for(const size of [{width:1366,height:768},{width:1920,height:1080}])for(const [route,title] of [['/access-denied','没有此页面的访问权限'],['/access-status-error','权限状态获取失败']]){
  await page.setViewportSize(size);await page.goto(route,{waitUntil:'networkidle'});await expect(page.getByRole('heading',{name:title})).toBeVisible();await page.evaluate(()=>document.fonts.ready)
  const state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,visibleText:document.body.innerText.slice(0,4000)}));const id=`ACCESS-${route.slice(1)}-B-${size.width}`,name=id+'.png',b=await page.screenshot({path:path.join(root,'originals',name)});entries.push({evidence_id:id,surface_id:'G006',expanded_case_id:id,source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'fresh isolated database; direct navigation, no simulated permission denial or failed lookup',steps:['navigate directly to '+route,'wait for initial status page','capture viewport'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED',limitation:'direct route rendering only; does not demonstrate actual permission denial, lookup error or retry'})
  await writeFile(path.join(root,'access-pages-manifest.json'),JSON.stringify(entries,null,2))
 }
})
