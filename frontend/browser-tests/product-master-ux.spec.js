import { expect, test } from '@playwright/test'

const categories = [
  { id:1,name:'照明分类',parent:null,sort_order:0,child_count:1,attributes:[],effective_attributes:[] },
  { id:2,name:'超长子分类名称用于产品主档窄桌面回归',parent:1,sort_order:0,child_count:0,attributes:[],effective_attributes:[] },
]
const product = { id:1,code:'P-001',name:'长名称产品'.repeat(8),name_en:'Long name product',sales_model_prefix:'PX',category:2,category_name:categories[1].name,additional_categories:[],suppliers:[1],status:'active',sku_count:2,parameter_count:1,certificate_count:0 }
function deferred() { let resolve; const promise=new Promise(r=>{resolve=r}); return {promise,resolve} }
async function fixture(page) {
  const state={rows:[product],writes:[],gate:deferred(),reads:0,failCategories:false,readOnly:false}
  await page.route('**/api/**', async route=>{
    const path=new URL(route.request().url()).pathname, method=route.request().method()
    if(path==='/api/session/current-operator/') return route.fulfill({json:state.readOnly ? {name:'Fixture read-only',rbac_enforcement:true,permissions:{products:{view:true},categories:{view:true},parameters:{view:true}},authenticated:true} : {name:'Isolated UX',development_superadmin:true,has_all_permissions:true,authenticated:true}})
    if(path==='/api/context/products/1/') return route.fulfill({json:{title:product.name,subtitle:product.code,badge:'在售',info:[['产品编号',product.code]],metrics:[],sections:[{key:'parameters',title:'产品参数',columns:[['name','参数']],rows:[{id:1,name:'功率'}]}]}})
    if(path==='/api/categories/tree/') return route.fulfill(state.failCategories ? {status:400,json:{detail:'分类加载失败'}} : {json:categories})
    if(path==='/api/categories/' && method==='GET') return route.fulfill({json:categories})
    if(path==='/api/suppliers/') return route.fulfill({json:[{id:1,name:'长供应商名称'.repeat(8)}]})
    if(path==='/api/products/next-code/') return route.fulfill({json:{code:'P-002'}})
    if(path==='/api/products/' && method==='GET') {state.reads++;return route.fulfill({json:state.rows})}
    if((path.startsWith('/api/products/') || path.startsWith('/api/categories/') || path.startsWith('/api/product-parameters/')) && ['POST','PUT','PATCH'].includes(method)) {
      state.writes.push(route.request().postDataJSON()); const result=await state.gate.promise
      if(result==='fail') return route.fulfill({status:400,json:{name:['测试重复记录，请修正']}})
      state.rows=[{...product,...state.writes.at(-1)}]; return route.fulfill({json:state.rows[0]})
    }
    if(path==='/api/product-parameters/') return route.fulfill({json:[{id:1,product:1,product_name:product.name,group:'基础规格',name:'功率',value:'10 / 20',unit:'W',sort_order:0}]})
    return route.fulfill({json:[]})
  })
  return state
}
for(const width of [1440,1280,1024]) test(`product filters, long content and pending save ${width}`,async({page})=>{
  await page.setViewportSize({width,height:1000});const state=await fixture(page)
  await page.goto('/products?search=PX&category=2&sort=sku')
  await expect(page.getByLabel('搜索产品')).toHaveValue('PX')
  await expect(page.getByLabel('产品分类筛选')).toHaveValue('2')
  await expect(page.getByLabel('产品排序')).toHaveValue('sku')
  const controls=await page.locator('.product-toolbar input,.product-toolbar select,.product-toolbar button').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,w:r.width}}))
  for(const r of controls){expect(r.x).toBeGreaterThanOrEqual(0);expect(r.right).toBeLessThanOrEqual(width);expect(r.w).toBeGreaterThan(30)}
  for(let i=0;i<controls.length;i++)for(let j=i+1;j<controls.length;j++){const a=controls[i],b=controls[j];expect(a.right<=b.x+1 || b.right<=a.x+1 || a.bottom<=b.y+1 || b.bottom<=a.y+1).toBeTruthy()}
  await page.getByRole('button',{name:'新建产品',exact:true}).click()
  const dialog=page.getByRole('dialog',{name:'新建产品'})
  await dialog.locator('input[required]').first().fill('异步保存产品')
  await dialog.locator('input[maxlength="30"]').fill('NEWPX')
  await dialog.getByRole('button',{name:'保存',exact:true}).dblclick()
  await expect.poll(()=>state.writes.length).toBe(1)
  await page.locator('.modal-backdrop').click({position:{x:2,y:2}})
  await expect(dialog).toBeVisible(); await expect(dialog.getByRole('button',{name:'取消',exact:true})).toBeDisabled()
  await page.getByRole('link',{name:'客户管理',exact:true}).dispatchEvent('click')
  await expect(page).toHaveURL('/customers')
  await page.evaluate(()=>history.back()); await expect(page).toHaveURL(/\/products\?/)
  await expect(dialog).toBeVisible(); expect(state.writes).toHaveLength(1)
  state.gate.resolve('success'); await expect(dialog).toHaveCount(0)
  await expect(page.locator('tbody')).toContainText('异步保存产品')
})
test('product detail URL survives reload and close preserves list filters',async({page})=>{
  await fixture(page);await page.goto('/products?search=PX&sort=sku');await page.locator('tbody tr').click()
  await expect(page).toHaveURL(/detail=1/);await expect(page.getByRole('button',{name:'关闭详情',exact:true})).toBeVisible()
  await page.reload();await expect(page.getByRole('button',{name:'关闭详情',exact:true})).toBeVisible()
  await page.getByRole('button',{name:'关闭详情',exact:true}).click();await expect(page).toHaveURL('/products?search=PX&sort=sku')
  await expect(page.getByLabel('搜索产品')).toHaveValue('PX')
})
test('product parameter to product detail closes back to original filtered list',async({page})=>{
  await fixture(page);await page.goto('/product-parameters?product=1');await page.locator('tbody .crm-customer-link').click()
  await expect(page).toHaveURL(/\/products\?detail=1&returnTo=/)
  await page.getByRole('button',{name:'关闭详情',exact:true}).click();await expect(page).toHaveURL('/product-parameters?product=1')
})
test('view-only fixtures cannot create/edit/delete through these page entries',async({page})=>{
  const state=await fixture(page);state.readOnly=true
  for(const path of ['/products','/categories','/product-parameters']){await page.goto(path);await expect(page.locator('.page-head h2')).toBeVisible();await expect(page.locator('.page-head .btn-primary')).toHaveCount(0);await expect(page.getByTitle('编辑产品')).toHaveCount(0);await expect(page.getByTitle('删除分类')).toHaveCount(0)}
})
test('product failure preserves input and retry; unsaved cancel requires confirmation',async({page})=>{
  const state=await fixture(page);await page.goto('/products');await page.getByTitle('编辑产品').click()
  const dialog=page.getByRole('dialog',{name:'编辑产品'})
  await dialog.locator('input[required]').first().fill('失败后保留产品')
  await dialog.getByRole('button',{name:'保存',exact:true}).click();state.gate.resolve('fail')
  await expect(dialog.getByRole('alert')).toContainText('测试重复记录')
  await expect(dialog.locator('input[required]').first()).toHaveValue('失败后保留产品')
  state.gate=deferred();await dialog.getByRole('button',{name:'保存',exact:true}).click()
  await expect.poll(()=>state.writes.length).toBe(2);state.gate.resolve('success');await expect(dialog).toHaveCount(0)
  await page.getByTitle('编辑产品').click();await dialog.locator('input[required]').first().fill('未保存修改')
  await dialog.getByRole('button',{name:'取消',exact:true}).click()
  await expect(page.getByRole('heading',{name:'未保存修改',exact:true})).toBeVisible()
  await page.getByRole('button',{name:'继续编辑',exact:true}).click();await expect(dialog).toBeVisible()
})
for(const width of [1440,1280,1024])test(`category search depth and retry ${width}`,async({page})=>{
  await page.setViewportSize({width,height:1000});const state=await fixture(page);state.failCategories=true
  await page.goto('/categories');await expect(page.getByText('分类加载失败',{exact:true})).toBeVisible()
  state.failCategories=false;await page.getByRole('button',{name:/重试|重新加载/}).click()
  await expect(page.locator('.tree-node')).toHaveCount(2)
  await page.getByRole('button',{name:'全部收起'}).click();await expect(page.locator('.tree-node')).toHaveCount(1)
  await expect(page.locator('.category-summary')).toContainText('最大层级2')
  await page.getByLabel('搜索分类').fill('超长');await expect(page.locator('.tree-node')).toHaveCount(1)
  await expect(page.locator('.tree-node')).toContainText('照明分类')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
})
test('category saving blocks backdrop, retains failure and permits retry',async({page})=>{
  const state=await fixture(page);await page.goto('/categories');await page.locator('.page-head').getByRole('button',{name:'新建根分类'}).click()
  const dialog=page.getByRole('dialog',{name:'新建分类'});await dialog.getByLabel('分类名称').fill('新分类')
  await dialog.getByRole('button',{name:'保存分类'}).dblclick();await expect.poll(()=>state.writes.length).toBe(1)
  await page.locator('.modal-backdrop').click({position:{x:2,y:2}});await expect(dialog).toBeVisible()
  state.gate.resolve('fail');await expect(dialog.getByRole('alert')).toContainText('测试重复记录');await expect(dialog.getByLabel('分类名称')).toHaveValue('新分类')
  state.gate=deferred();await dialog.getByRole('button',{name:'保存分类'}).click();await expect.poll(()=>state.writes.length).toBe(2);state.gate.resolve('success');await expect(dialog).toHaveCount(0)
})
test('product parameter context and pending save failure remain recoverable',async({page})=>{
  const state=await fixture(page);await page.goto('/product-parameters?product=1')
  await expect(page.getByLabel('按产品筛选参数')).toHaveValue('1')
  await expect(page.getByText('产品参数用于记录通用规格。',{exact:false})).toBeVisible()
  await page.locator('.page-head .btn-primary').click();const dialog=page.getByRole('dialog')
  await dialog.getByLabel('参数名称',{exact:true}).fill('输入保留');await dialog.getByLabel('参数值',{exact:true}).fill('20')
  await dialog.getByRole('button',{name:'保存',exact:true}).dblclick();await expect.poll(()=>state.writes.length).toBe(1)
  expect(Number(state.writes[0].product)).toBe(1)
  await page.locator('.modal-backdrop').click({position:{x:2,y:2}});await expect(dialog).toBeVisible()
  state.gate.resolve('fail');await expect(dialog.getByRole('alert')).toContainText('测试重复记录');await expect(dialog.getByLabel('参数名称',{exact:true})).toHaveValue('输入保留')
})
for(const width of [1440,1280,1024])test(`parameter long layout and empty reset ${width}`,async({page})=>{
  await page.setViewportSize({width,height:1000});await fixture(page);await page.goto('/product-parameters?product=1')
  await expect(page.locator('tbody tr')).toHaveCount(1)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  for(const rect of await page.locator('.parameter-filter-bar button,.parameter-filter-bar select').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {x:r.x,right:r.right,width:r.width}}))){expect(rect.x).toBeGreaterThanOrEqual(0);expect(rect.right).toBeLessThanOrEqual(width);expect(rect.width).toBeGreaterThan(35)}
  await page.route('**/api/product-parameters/?**',route=>route.fulfill({json:[]}))
  await page.getByRole('button',{name:'刷新',exact:true}).click();await expect(page.locator('tbody tr')).toHaveCount(0)
  await expect(page.getByText('暂无产品参数',{exact:false})).toBeVisible()
})
test('category drag preserves selected node and collapsed state after reorder',async({page})=>{
  const state=await fixture(page);state.gate.resolve('success');await page.goto('/categories')
  await page.getByRole('button',{name:'全部收起'}).click()
  // HTML5 events use a real DataTransfer; the actual drop target receives the drag.
  const transfer=await page.evaluateHandle(()=>new DataTransfer())
  await page.locator('.tree-node').first().dispatchEvent('dragstart',{dataTransfer:transfer})
  await page.locator('.root-drop').dispatchEvent('drop',{dataTransfer:transfer})
  await expect.poll(()=>state.writes.length).toBe(1)
  expect(state.writes[0]).toEqual({id:1,parent:null,index:1})
  await expect(page.locator('.tree-node')).toHaveCount(1)
  await expect(page.locator('.tree-node.active')).toContainText('照明分类')
})

for (const width of [1440, 1280, 1024]) test(`R0-F9 products status labels stay on one line ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 1000 })
  await fixture(page)
  await page.goto('/products')
  await expect(page.locator('.product-list-table .tag').first()).toBeVisible()
  for (const label of await page.locator('.product-list-table .tag').all()) {
    const box = await label.evaluate(el => {
      const range = document.createRange(); range.selectNodeContents(el)
      const rect = range.getBoundingClientRect(); const cell = el.closest('td').getBoundingClientRect()
      return { height: rect.height, lineHeight: parseFloat(getComputedStyle(el).lineHeight), left: rect.left, right: rect.right, cellLeft: cell.left, cellRight: cell.right }
    })
    expect(box.height).toBeLessThanOrEqual(box.lineHeight + 1)
    expect(box.left).toBeGreaterThanOrEqual(box.cellLeft)
    expect(box.right).toBeLessThanOrEqual(box.cellRight)
  }
})
