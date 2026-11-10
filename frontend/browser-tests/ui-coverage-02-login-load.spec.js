import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('login and customer load failure states',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, entries=[]
 await mkdir(path.join(root,'originals'),{recursive:true})
 async function capture(p,id,surface,role,steps,simulated){
  const state=await p.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,visibleText:document.body.innerText.slice(0,4000)}))
  const name=`${id}.png`,b=await p.screenshot({path:path.join(root,'originals',name)})
  entries.push({evidence_id:id,surface_id:surface,source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role,steps,simulated,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED'})
  await writeFile(path.join(root,'login-load-manifest.json'),JSON.stringify(entries,null,2))
 }
 const anon=await browser.newContext({viewport:{width:1366,height:768},deviceScaleFactor:1})
 const login=await anon.newPage(); await login.goto('/login',{waitUntil:'networkidle'}); await capture(login,'LOGIN-B-1366','G005','unauthenticated',['open login in a fresh browser context'],false); await anon.close()
 const matcher=url=>url.pathname==='/api/customers/'
 const fail=route=>route.request().method()==='GET' ? route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Simulated service unavailable'})}) : route.continue()
 await page.route(matcher,fail); await page.goto('/customers',{waitUntil:'networkidle'}); await capture(page,'CUSTOMERS-FIRST-503-LOADING-B-1366','G022','authenticated codex test superuser',['intercept customer list GET with simulated 503','navigate to customer list','capture during automatic retries'],true); await expect(page.getByText('数据加载失败')).toBeVisible({timeout:30000}); await capture(page,'CUSTOMERS-FIRST-503-ERROR-B-1366','G022','authenticated codex test superuser',['intercept customer list GET with simulated 503','navigate to customer list','wait for automatic retries to finish'],true)
 await page.unroute(matcher,fail); await page.reload({waitUntil:'networkidle'}); await expect(page.locator('table tbody tr').first()).toBeVisible()
 await page.route(matcher,fail); await page.getByRole('button',{name:'刷新',exact:true}).click(); await page.waitForTimeout(500); await capture(page,'CUSTOMERS-REFRESH-503-LOADING-B-1366','G022','authenticated codex test superuser',['load real synthetic customer rows','intercept customer list GET with simulated 503','click refresh','capture during automatic retries'],true); await expect(page.getByText('刷新失败，当前显示上一次成功加载的数据。',{exact:false})).toBeVisible({timeout:30000}); await capture(page,'CUSTOMERS-REFRESH-503-ERROR-B-1366','G022','authenticated codex test superuser',['load real synthetic customer rows','intercept customer list GET with simulated 503','click refresh','wait for automatic retries to finish'],true)
})
