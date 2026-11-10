import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import path from 'node:path'
test.use({channel:'chrome',deviceScaleFactor:1})
test('order numeric field wheel observation',async({page,browser})=>{
 test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
 for(const size of [{width:1366,height:768},{width:390,height:844}]){
  await page.setViewportSize(size);await page.goto('/orders',{waitUntil:'networkidle'});await page.getByRole('button',{name:'新建订单',exact:true}).click();const modal=page.locator('.modal-backdrop .modal'),input=modal.getByLabel('交期天数');await input.fill('7');await input.focus();const box=await input.boundingBox();const before=await input.inputValue();await page.mouse.move(box.x+box.width/2,box.y+box.height/2)
  async function capture(stage,after){const state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale}));const id=`ORDER-LEAD-WHEEL-${stage}-B-${size.width}`,name=id+'.png',b=await page.screenshot({path:path.join(root,'originals',name)});entries.push({evidence_id:id,surface_id:'S016',expanded_case_id:id,source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'fresh isolated database; unsaved synthetic order',steps:['open new order','enter 7 lead-time days','focus input',...(stage==='AFTER'?['wheel upward over input']:[])],before,after,simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED'});await writeFile(path.join(root,'order-wheel-v2-manifest.json'),JSON.stringify(entries,null,2))}
  await capture('BEFORE',before);await page.mouse.wheel(0,-300);await page.waitForTimeout(300);await capture('AFTER',await input.inputValue());await modal.getByRole('button',{name:'取消',exact:true}).click();await page.getByRole('button',{name:'放弃修改',exact:true}).click();await expect(modal).toHaveCount(0)
 }
})
