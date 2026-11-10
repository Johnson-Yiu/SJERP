import {test} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1920,height:1080},deviceScaleFactor:1})
test('baseline route views with isolated workspace fixture',async({page,browser})=>{
 test.setTimeout(240000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 const routes=[['/','G018'],['/new-product-reminders','G087'],['/finance-ledger','F027'],['/sku-trade-units','P047'],['/reports','F047'],['/historical-orders','F045'],['/categories','P035'],['/products','P001'],['/skus','P023'],['/sku-packaging','P039'],['/hs-codes','P044'],['/quotes','S001'],['/orders','S015'],['/import','F032'],['/history-preflight','F035'],['/history-takeover','F037'],['/organization','G019'],['/inventory','P050'],['/purchase-orders','S033'],['/finance','F001'],['/receivables','F004'],['/payables','F004'],['/transactions','F008'],['/rmb-cash-events','F021'],['/suppliers','G024'],['/customers','G022'],['/contacts','G026'],['/follow-ups','G028'],['/inventory-movements','G030'],['/product-parameters','G032'],['/product-certificates','G034']]
 for(const [route,surface] of routes){
  const id=route==='/'?'root':route.slice(1);let error=null
  try{await page.goto(route,{waitUntil:'networkidle',timeout:20000});await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})))})}catch(e){error=String(e)}
  const state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,title:document.title,visibleText:document.body.innerText.slice(0,3000)}))
  const name=`BASE-B-${id}-1920.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  entries.push({evidence_id:name,surface_id:surface,expanded_case_id:`BASE-B-${id}-1920`,source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),requested_route:route,...state,role:'authenticated codex test superuser',data:'isolated workspace synthetic fixture; route initial state only',steps:['navigate directly to route','wait for network idle and fonts/images where possible','capture viewport'],simulated:false,navigation_error:error,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED'})
  await writeFile(path.join(root,'route-baseline-1920-manifest.json'),JSON.stringify(entries,null,2))
 }
})
