import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',deviceScaleFactor:1})
test('login initial and expired prompt',async({browser})=>{
 test.setTimeout(60000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1});const page=await context.newPage()
 for(const [route,id,text] of [['/login','LOGIN-B-1920','请输入分配给你的账号。'],['/login?reason=expired','LOGIN-EXPIRED-B-1920','登录已过期，请重新登录。']]){
  await page.goto(route,{waitUntil:'networkidle'});await expect(page.getByText(text,{exact:true})).toBeVisible();await page.evaluate(()=>document.fonts.ready);const state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,visibleText:document.body.innerText.slice(0,2000)}));const name=id+'.png',b=await page.screenshot({path:path.join(root,'originals',name)});entries.push({evidence_id:id,surface_id:'G005',expanded_case_id:id,source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'unauthenticated',data:'fresh browser context and isolated server',steps:['navigate directly to '+route,'capture login page'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED',limitation:'expired query renders message; no actual session expiry was induced'});await writeFile(path.join(root,'login-variants-manifest.json'),JSON.stringify(entries,null,2))
 }
 await context.close()
})
