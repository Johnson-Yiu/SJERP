# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui-coverage-02-order-wheel.spec.js >> order numeric field wheel observation
- Location: browser-tests\ui-coverage-02-order-wheel.spec.js:6:1

# Error details

```
Error: expect(locator).toHaveValue(expected) failed

Locator:  locator('.modal-backdrop .modal').getByLabel('交期天数')
Expected: "7"
Received: "8"
Timeout:  5000ms

Call log:
  - Expect "toHaveValue" locator('.modal-backdrop .modal').getByLabel('交期天数') with timeout 5000ms
  - waiting for locator('.modal-backdrop .modal').getByLabel('交期天数')
    14 × locator resolved to <input min="0" step="1" type="number" placeholder="天数" aria-label="交期天数" data-v-dfaf05d4=""/>
       - unexpected value "8"

```

```yaml
- spinbutton "交期天数": "8"
```

# Test source

```ts
  1  | import {test,expect} from '@playwright/test'
  2  | import {mkdir,writeFile} from 'node:fs/promises'
  3  | import {createHash} from 'node:crypto'
  4  | import path from 'node:path'
  5  | test.use({channel:'chrome',deviceScaleFactor:1})
  6  | test('order numeric field wheel observation',async({page,browser})=>{
  7  |  test.setTimeout(90000);const root=process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT,entries=[];await mkdir(path.join(root,'originals'),{recursive:true})
  8  |  for(const size of [{width:1366,height:768},{width:390,height:844}]){
> 9  |   await page.setViewportSize(size);await page.goto('/orders',{waitUntil:'networkidle'});await page.getByRole('button',{name:'新建订单',exact:true}).click();const modal=page.locator('.modal-backdrop .modal'),input=modal.getByLabel('交期天数');await input.fill('7');await input.focus();const box=await input.boundingBox();const before=await input.inputValue();await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.wheel(0,-300);await page.waitForTimeout(300);const after=await input.inputValue();const state=await page.evaluate(()=>({route:location.pathname+location.search,viewport_actual:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,zoom:visualViewport.scale,visibleText:document.body.innerText.slice(0,3000)}));const id=`ORDER-LEAD-WHEEL-B-${size.width}`,name=id+'.png',b=await page.screenshot({path:path.join(root,'originals',name)});entries.push({evidence_id:id,surface_id:'S016',expanded_case_id:id,source_branch:'codex/first-release-independent-review-02',source_sha:'c90cacaa99a468d92dd61c41437834c5d8acb094',browser_version:browser.version(),...state,role:'authenticated codex test superuser',data:'fresh isolated database; unsaved synthetic order',steps:['open new order','enter 7 lead-time days','focus input and wheel upward over it','capture after wheel'],before,after,simulated:false,capture_time_utc:new Date().toISOString(),file:`originals/${name}`,sha256:createHash('sha256').update(b).digest('hex'),pixels:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)},review:'NOT_REVIEWED'});await writeFile(path.join(root,'order-wheel-manifest.json'),JSON.stringify(entries,null,2));await expect(input).toHaveValue(before);await modal.getByRole('button',{name:'取消',exact:true}).click();await page.getByRole('button',{name:'放弃修改',exact:true}).click();await expect(modal).toHaveCount(0)
     |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         ^ Error: expect(locator).toHaveValue(expected) failed
  10 |  }
  11 | })
  12 | 
```