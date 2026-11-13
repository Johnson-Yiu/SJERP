import {test,expect} from '@playwright/test'
import {writeFile} from 'node:fs/promises'
test.skip(process.env.ISOLATED_PLAYWRIGHT_TEST_FILE !== 'prelaunch-ui-category-tabs-02.spec.js', 'Dedicated authenticated isolated real Chrome profile required.')
test.setTimeout(120000)
async function post(page,url,data){const token=(await page.context().cookies()).find(c=>c.name==='csrftoken')?.value;const r=await page.request.post('/api'+url,{data,headers:{'X-CSRFToken':token}});expect(r.status(),await r.text()).toBe(201);return r.json()}
for(const [width,height] of [[1280,800],[1366,768],[1920,1080]]) test(`category source wrapping and candidate selection ${width}`,async({page},info)=>{
 await page.setViewportSize({width,height})
 const rootName='合成超长来源分类商业展厅照明安装附件电源系列'+width
 const root=await post(page,'/categories/',{name:rootName})
 const child=await post(page,'/categories/',{name:'合成子分类'+width,parent:root.id})
 await post(page,'/category-attributes/',{category:root.id,name:'额定功率',key:'power',include_in_sku:true})
 await page.goto('/categories');await page.getByRole('button',{name:'全部展开'}).click()
 await page.locator('.tree-node').filter({hasText:rootName}).click()
 await page.locator('.source-badge').first().scrollIntoViewIfNeeded()
 await page.screenshot({path:info.outputPath('category-current-short.png')})
 await page.locator('.tree-node').filter({hasText:child.name}).click()
 const badge=page.locator('.source-badge.inherited').first();await expect(badge).toContainText(rootName)
 await badge.scrollIntoViewIfNeeded();await expect(badge).toBeInViewport()
 const box=await badge.boundingBox();expect(box.x+box.width).toBeLessThanOrEqual(width)
 expect(await badge.evaluate(el=>el.scrollWidth<=el.clientWidth+1)).toBe(true)
 await page.screenshot({path:info.outputPath('category-inherited-long.png')})
 await page.goto('/products');await page.getByRole('button',{name:'新建产品',exact:true}).click()
 const form=page.getByRole('dialog',{name:'新建产品',exact:true})
 await form.locator('.category-select').first().click()
 await form.locator('.cascade-option').filter({hasText:rootName}).click()
 await form.locator('.cascade-option').filter({hasText:child.name}).click()
 await expect(form.locator('.category-select').first()).toContainText(child.name)
 await form.getByPlaceholder('如：BTY橱柜电源').fill('合成分类保存'+width)
 await form.getByPlaceholder('如：BTY、COB320、SMD120').fill('CAT'+width)
 await page.screenshot({path:info.outputPath('product-category-selected.png')})
 const saved=page.waitForResponse(r=>r.url().endsWith('/products/')&&r.request().method()==='POST')
 await form.getByRole('button',{name:/保存/}).click();const r=await saved;expect(r.status(),await r.text()).toBe(201)
 const product=await r.json();expect(product.category).toBe(child.id)
 const read=await (await page.request.get('/api/products/'+product.id+'/')).json();expect(read.category).toBe(child.id)
 await writeFile(info.outputPath('result.json'),JSON.stringify({width,height,root,child,product:product.id},null,2))
})

test('six and twelve workspaces keep activation local and permit narrow manual scroll',async({page},info)=>{
 await page.setViewportSize({width:1366,height:768})
 const names=[]
 for(let i=0;i<11;i++){const name='合成长标题客户商业照明跨区域采购项目验收'+i;names.push(name);await post(page,'/customers/',{code:'TAB'+i,name,country:'CN',contacts:[{name:'合成联系人'}]})}
 await page.goto('/customers')
 for(let i=0;i<11;i++){
  await page.getByRole('row').filter({has:page.getByText(names[i],{exact:true})}).getByRole('button',{name:'查看详情',exact:true}).click()
  if(i===4||i===10){
   const count=await page.getByRole('tab').count();expect(count).toBe(i+2)
   const active=page.locator('[role=tab][aria-selected=true]');await expect(active).toBeInViewport()
   await page.screenshot({path:info.outputPath('tabs-'+count+'.png')})
  }
  await page.getByRole('tab',{name:'客户管理',exact:true}).click()
 }
 await page.setViewportSize({width:390,height:844})
 const list=page.getByRole('tablist');await list.hover();await page.mouse.wheel(1000,0)
 await expect.poll(()=>list.evaluate(el=>el.scrollLeft)).toBeGreaterThan(0)
 const last=page.getByRole('tab').last();await last.click();await expect(last).toHaveAttribute('aria-selected','true')
 await expect(last).toBeInViewport();await page.screenshot({path:info.outputPath('tabs-12-narrow.png')})
 await last.press('Home');await expect(page.getByRole('tab').first()).toHaveAttribute('aria-selected','true')
 expect(await page.evaluate(()=>scrollX)).toBe(0)
})

test.beforeEach(async({page})=>{page.setDefaultTimeout(30000)})
