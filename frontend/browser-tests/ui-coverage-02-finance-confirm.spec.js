import {test,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
import path from 'node:path'
import {createHash} from 'node:crypto'
test.use({channel:'chrome',viewport:{width:1366,height:768},deviceScaleFactor:1})
test('A transaction dirty close',async({page,browser})=>{
 test.setTimeout(120000)
 const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[]
 await mkdir(path.join(root,'originals'),{recursive:true})
 async function capture(stage){
  await page.evaluate(()=>document.fonts.ready)
  const data=await page.evaluate(()=>{
   const read=sel=>{const e=document.querySelector(sel);if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {text:e.innerText.slice(0,500),rect:{x:r.x,y:r.y,width:r.width,height:r.height},zIndex:s.zIndex,display:s.display,visibility:s.visibility,centerHit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML.slice(0,300)}}
   return {route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,mask:read('.mask'),confirmation:read('.app-dialog-backdrop'),confirmButton:read('[data-testid="dialog-cancel"]')}
  })
  const name=`ULR005-A-${stage}.png`,b=await page.screenshot({path:path.join(root,'originals',name),fullPage:false})
  entries.push({evidence_id:name,surface_id:'F017',expanded_case_id:`ULR005-A-${stage}`,related_ulr:['ULR-005'],source_branch:'codex/finance-receipt-optimization-02',source_sha:'c978758f37db8b8acf5e751fc7aa836287163a6b',browser_version:browser.version(),...data,role:'authenticated codex test superuser',data:'new isolated SQLite, unsaved synthetic note only',steps:['open /transactions','open 新增记账','enter synthetic note','close form'],simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}})
  await writeFile(path.join(root,'finance-confirm-manifest.json'),JSON.stringify(entries,null,2))
 }
 await page.goto('/transactions',{waitUntil:'domcontentloaded'})
 const add=page.getByRole('button',{name:'新增记账',exact:true});await expect(add).toBeEnabled();await add.click()
 const form=page.getByRole('dialog',{name:'新增记账'})
 await form.getByLabel('备注',{exact:true}).fill('隔离验收未保存备注')
 await capture('dirty')
 await form.getByRole('button',{name:'关闭',exact:true}).click()
 await expect(page.getByText('未保存修改',{exact:false}).first()).toBeAttached()
 await capture('after-close')
 let result
 try {await page.getByRole('button',{name:'继续编辑',exact:true}).click({timeout:3000});result={outcome:'clicked'}}
 catch(error){result={outcome:'blocked',error:String(error)}}
 await writeFile(path.join(root,'finance-confirm-click.json'),JSON.stringify(result,null,2))
 await capture('after-click')
})
