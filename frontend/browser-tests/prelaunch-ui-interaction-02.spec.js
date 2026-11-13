import {existsSync,readFileSync,writeFileSync} from 'node:fs'
import {execFileSync} from 'node:child_process'
import {writeFile} from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
import {createHash} from 'node:crypto'
import {test,expect} from '@playwright/test'
test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== 'prelaunch-ui-interaction-02.spec.js', 'Dedicated authenticated isolated real Chrome profile required.')
test.setTimeout(120000)
let fixture, salesFixture
const sku='EVID-TRACK-LONG-SKU-3000K-BEAM24-BLACK-01'
test.beforeAll(()=>{const cache=process.env.ISOLATED_TEST_ROOT+'/d-ui-fixtures.json';if(existsSync(cache)){({fixture,salesFixture}=JSON.parse(readFileSync(cache,'utf8')));return;}salesFixture=JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON,[fileURLToPath(new URL('../../docs/uat-evidence/ui-sales-completion-02/seed.py',import.meta.url))],{encoding:'utf8'}));fixture=JSON.parse(execFileSync(process.env.ISOLATED_TEST_PYTHON,[fileURLToPath(new URL('../../docs/uat-evidence/ui-final-state-closeout-03/seed.py',import.meta.url))],{encoding:'utf8'}));writeFileSync(cache,JSON.stringify({fixture,salesFixture}))})
for(const [width,height] of [[1366,768],[1920,1080]]) {
test(`inventory actual pointer, wheel, workspace and confirmation ${width}`,async({page,browser},info)=>{
 test.setTimeout(120000)
 await page.setViewportSize({width,height})
 const states=[]
 async function snap(name){const png=await page.screenshot({path:info.outputPath(name+'.png')});states.push({name,sha256:createHash('sha256').update(png).digest('hex')})}
 await page.goto('/inventory-movements')
 await page.getByRole('button',{name:'新建库存调整',exact:true}).click()
 const form=page.getByRole('dialog',{name:'新建手工库存流水'})
 const checkbox=form.locator('label').filter({hasText:sku}).getByRole('checkbox')
 await checkbox.scrollIntoViewIfNeeded()
 const b=await checkbox.boundingBox()
 await checkbox.click({position:{x:2,y:b.height/2}})
 await expect(checkbox).toBeChecked()
 const qty=form.getByRole('spinbutton',{name:sku+' 数量',exact:true})
 await qty.fill('2');await qty.hover();await page.mouse.wheel(0,500)
 await expect(qty).toHaveValue('2')
 await snap('inventory-selected-wheel-unchanged')
 await page.locator('.sidebar').getByRole('link',{name:'客户管理',exact:true}).click()
 await expect(form).toBeHidden()
 await page.getByRole('tab',{name:/库存流水 · 新建/}).click()
 await expect(form).toBeVisible();await expect(qty).toHaveValue('2')
 await form.getByRole('button',{name:'取消',exact:true}).click()
 const stay=page.getByRole('button',{name:'继续编辑',exact:true})
 await expect(stay).toBeFocused()
 await page.keyboard.press('Shift+Tab');await expect(page.getByTestId('dialog-confirm')).toBeFocused()
 await page.keyboard.press('Tab');await expect(stay).toBeFocused()
 await snap('unsaved-confirm-over-parent')
 await stay.click();await expect(qty).toHaveValue('2')
 const saved=page.waitForResponse(r=>r.url().endsWith('/inventory-movements/batch/')&&r.request().method()==='POST')
 await form.getByRole('button',{name:'保存 1 条流水',exact:true}).click()
 const response=await saved;expect(response.status(),await response.text()).toBe(201)
 const [movement]=await response.json()
 const read=await page.request.get('/api/inventory-movements/'+movement.id+'/');expect(read.ok()).toBe(true);expect(Number((await read.json()).quantity)).toBe(2)
 await expect(form).toBeHidden();await snap('inventory-saved')
 await page.getByRole('button',{name:'新建库存调整',exact:true}).click()
 await form.locator('label').filter({hasText:sku}).getByRole('checkbox').check()
 await form.getByRole('button',{name:'取消',exact:true}).click()
 await page.getByRole('button',{name:'放弃修改',exact:true}).click();await expect(form).toBeHidden()
 await writeFile(info.outputPath('result.json'),JSON.stringify({source:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),browser:browser.version(),width,height,metrics:await page.evaluate(()=>({dpr:devicePixelRatio,width:innerWidth,height:innerHeight})),movement:movement.id,states},null,2))
})
test(`reminder list focus and real save ${width}`,async({page},info)=>{
 await page.setViewportSize({width,height})
 const customers=await (await page.request.get('/api/customers/')).json();const customer=(customers.results||customers)[0]
 for(let i=0;i<12;i++){const r=await post(page, '/api/new-product-reminders/',{data:{customer:customer.id,requirement:`合成提醒 ${width} ${i}`,request_key:crypto.randomUUID()}});expect(r.status(),await r.text()).toBe(201)}
 await page.goto('/new-product-reminders?search='+encodeURIComponent('合成提醒 '+width))
 await expect(page.locator('.requirement')).toHaveCount(12)
 const trigger=page.getByRole('button',{name:'记录新品需求',exact:true})
 await trigger.click()
 const heading=page.getByRole('heading',{name:'记录新品需求',exact:true})
 await expect(heading).toBeFocused();await expect(heading).toBeInViewport()
 await page.screenshot({path:info.outputPath('reminder-focus-long-list.png')})
 await page.locator('.editor').getByRole('button',{name:'取消',exact:true}).click();await expect(trigger).toBeFocused()
 await expect(page.getByPlaceholder('产品、规格、其他要求或客户')).toHaveValue('合成提醒 '+width)
 await trigger.click();await page.locator('.editor select').first().selectOption(String(customer.id))
 await page.getByLabel('所找产品',{exact:true}).fill('实际保存需求 '+width)
 const saved=page.waitForResponse(r=>r.url().endsWith('/new-product-reminders/')&&r.request().method()==='POST')
 await page.getByRole('button',{name:'保存需求',exact:true}).click()
 const response=await saved;expect(response.status()).toBe(201);const record=await response.json()
 expect((await (await page.request.get('/api/new-product-reminders/'+record.id+'/')).json()).requirement).toBe('实际保存需求 '+width)
 await page.getByRole('button',{name:'返回需求列表',exact:true}).click()
 await expect(page.getByPlaceholder('产品、规格、其他要求或客户')).toHaveValue('合成提醒 '+width)
 await page.screenshot({path:info.outputPath('reminder-return-filter-preserved.png')})
})
}

for(const [width,height] of [[1366,768],[1920,1080]]) {
test(`receipt footer and actual required validation ${width}`,async({page},info)=>{
 test.setTimeout(120000)
 await page.setViewportSize({width,height})
 if(width===1366){const placed=await post(page, `/api/purchase-orders/${fixture.purchase}/place/`,{data:{}});expect(placed.status(),await placed.text()).toBe(200)}
 await page.goto('/purchase-orders?detail='+fixture.purchase)
 const parent=page.getByRole('dialog',{name:'采购工作台'})
 await parent.getByRole('button',{name:/到货.*入库|验货.*入库|收货/}).first().click()
 await parent.getByRole('button',{name:'验货入库',exact:true}).first().click()
 const form=page.getByRole('dialog',{name:'验货合格入库'})
 const submit=form.getByRole('button',{name:'确认入库',exact:true})
 const b=await submit.boundingBox();expect(b.y).toBeGreaterThan(0);expect(b.y+b.height).toBeLessThanOrEqual(height)
 await page.screenshot({path:info.outputPath('receipt-initial-footer.png')})
 await submit.click();await expect(form).toBeVisible()
 await expect(form.getByRole('checkbox',{name:'已核对型号、数量及外观，仅登记合格品'})).toBeFocused()
 await form.getByLabel('本次合格入库数量 *',{exact:true}).fill('1')
 await form.getByRole('checkbox',{name:'已核对型号、数量及外观，仅登记合格品'}).check()
 const saved=page.waitForResponse(r=>r.url().endsWith('/receive/')&&r.request().method()==='POST')
 await submit.click();const response=await saved;expect(response.status(),await response.text()).toBe(201)
 await expect(form).toBeHidden()
 const purchase=await (await page.request.get(`/api/purchase-orders/${fixture.purchase}/`)).json()
 expect(Number(purchase.items[0].received_quantity)).toBe(width===1366?1:2)
 await page.screenshot({path:info.outputPath('receipt-saved.png')})
})
test(`PI nested preview scroll close and persisted content ${width}`,async({page},info)=>{
 await page.setViewportSize({width,height});await page.goto('/quotes?detail='+salesFixture.quote)
 await page.getByRole('button',{name:'预览 PI',exact:true}).first().click()
 const modal=page.getByRole('dialog',{name:'PI 预览'})
 const close=modal.getByRole('button',{name:'关闭预览'})
 const b=await close.boundingBox();expect(b.y).toBeGreaterThanOrEqual(0);expect(b.y+b.height).toBeLessThanOrEqual(height)
 const frame=modal.frameLocator('iframe[title="已保存 PI"]')
 await expect(frame.locator('tbody img').first()).toBeVisible()
 const content=await frame.locator('body').innerText();expect(content.length).toBeGreaterThan(100)
 await modal.locator('iframe').hover();await page.mouse.wheel(0,900)
 await page.screenshot({path:info.outputPath('pi-preview-scrolled.png')})
 await close.click();await expect(modal).toBeHidden()
 const saved=await (await page.request.get('/api/quotes/'+salesFixture.quote+'/')).json()
 await writeFile(info.outputPath('saved-quote.json'),JSON.stringify(saved,null,2))
 await expect(page.getByRole('button',{name:'预览 PI',exact:true}).first()).toBeVisible()
})
}

test('summary card counts and layout across affected pages',async({page},info)=>{
 test.setTimeout(180000)
 const states=[]
 for(const [width,height] of [[1366,768],[1920,1080],[390,844]]) {
  await page.setViewportSize({width,height})
  for(const route of ['/customers','/suppliers','/products','/skus','/orders','/purchase-orders','/transactions','/receivables','/payables','/sku-packaging','/hs-codes','/contacts','/follow-ups','/product-certificates']) {
   await page.goto(route)
   const cards=page.locator('.summary-cards').first();await expect(cards).toBeVisible()
   const grid=await cards.evaluate(el=>({columns:getComputedStyle(el).gridTemplateColumns.split(' ').length,width:el.clientWidth}))
   expect([1,2,4]).toContain(grid.columns)
   states.push({route,width,...grid})
   await page.screenshot({path:info.outputPath(`cards-${route.slice(1)}-${width}.png`)})
  }
 }
 for(const query of ['', 'EVID', 'nonexistent-customer-ui-02']) {
  const response=await page.request.get('/api/customers/?search='+query);const data=await response.json();const count=data.count??data.length
  await page.goto('/customers?search='+query)
  const metric=page.locator('.summary-cards article').filter({hasText:'客户数量'})
  await expect(metric.locator('strong')).toHaveText(String(count))
  await expect(metric).toContainText('当前筛选结果（含全部页）')
 }
 await writeFile(info.outputPath('card-results.json'),JSON.stringify(states,null,2))
})
for(const [width,height] of [[1366,768],[1920,1080]]) test(`rich text real keyboard selection and saved link ${width}`,async({page},info)=>{
 await page.setViewportSize({width,height});await page.goto('/quotes?detail='+salesFixture.quote)
 await page.locator('.workbench-tabs').getByRole('button',{name:/重要备注/}).click()
 await page.getByRole('button',{name:'新增备注',exact:true}).click()
 const editor=page.locator('.rich-editable');await editor.fill('实际链接选择 '+width)
 await editor.press('Control+a')
 await page.getByRole('button',{name:'插入链接',exact:true}).click()
 await page.getByTestId('dialog-input').fill('https://example.test/'+width)
 await page.getByTestId('dialog-confirm').click()
 await expect(editor.locator('a')).toHaveText('实际链接选择 '+width)
 await expect(editor.locator('a')).toHaveAttribute('href','https://example.test/'+width)
 await editor.click();await editor.press('End')
 await page.getByRole('button',{name:'插入链接',exact:true}).click()
 await page.getByTestId('dialog-input').fill('javascript:alert(1)')
 await page.getByTestId('dialog-confirm').click()
 await expect(page.getByText('链接格式不支持',{exact:true})).toBeVisible();await page.getByTestId('dialog-confirm').click()
 await expect(editor.locator('a')).toHaveCount(1)
 await page.screenshot({path:info.outputPath('rich-link-selection.png')})
 const saved=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().includes('important-notes'))
 await page.getByRole('button',{name:'保存重要备注',exact:true}).click();const result=await saved;expect(result.ok(),await result.text()).toBe(true)
 await page.reload();await page.locator('.workbench-tabs').getByRole('button',{name:/重要备注/}).click()
 await expect(page.locator('.important-note-content a').filter({hasText:'实际链接选择 '+width})).toHaveAttribute('href','https://example.test/'+width)
 await page.screenshot({path:info.outputPath('rich-link-reopened.png')})
})

async function post(page,url,options) {
 const token=(await page.context().cookies()).find(c=>c.name==='csrftoken')?.value
 return page.request.post(url,{...options,headers:{...options?.headers,'X-CSRFToken':token}})
}

test.afterEach(async({page,browser},info)=>{
 await page.screenshot({path:info.outputPath('final-state.png')}).catch(()=>{})
 await writeFile(info.outputPath('environment.json'),JSON.stringify({source:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),browser:browser.version(),viewport:page.viewportSize(),metrics:await page.evaluate(()=>({dpr:devicePixelRatio,width:innerWidth,height:innerHeight})).catch(()=>null),status:info.status},null,2))
})
