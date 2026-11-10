import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('finance ledger scrollable initial forms',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[]; await mkdir(path.join(root,'originals'),{recursive:true})
 await page.goto('/finance-ledger',{waitUntil:'networkidle'}); await page.evaluate(()=>document.fonts.ready)
 for(const [label,surface] of [['登记与复核','F029'],['账户与映射','F028'],['转账与分类','F031']]){
  await page.evaluate(()=>window.scrollTo(0,0)); const button=page.getByRole('button',{name:label,exact:true}); await button.click(); await expect(button).toHaveAttribute('aria-pressed','true')
  await page.mouse.move(1100,650); await page.mouse.wheel(0,1800); await page.waitForTimeout(500)
  const state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,scrollY,scrollHeight:document.documentElement.scrollHeight,visibleText:document.body.innerText.slice(0,6000)})); const id=`LEDGER-${surface}-SCROLL-B-1366`,name=id+'.png',b=await page.screenshot({path:path.join(root,'originals',name)})
  entries.push({evidence_id:id,surface_id:surface,expanded_case_id:id,source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'isolated workspace fixture, empty finance data',steps:['navigate to /finance-ledger','click '+label,'scroll page with mouse wheel','capture viewport'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED',limitation:'initial empty forms only; no submitted operations'})
  await writeFile(path.join(root,'ledger-scroll-manifest.json'),JSON.stringify(entries,null,2))
 }
})
