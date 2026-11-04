import { expect,test } from '@playwright/test'
const product={id:1,code:'F7-P',name:'多规格灯具长名称'.repeat(5),category:1,sales_model_prefix:'F7',combination_rules:[]}
const attributes=[{id:1,category_id:1,key:'power',name:'功率',unit:'W',required:true,include_in_sku:true,include_in_sales_model:false},{id:2,category_id:1,key:'voltage',name:'电压',unit:'V',required:true,include_in_sku:true,include_in_sales_model:false}]
const existing={id:7,sku:'SKU-F7',sku_code:'SKU-F7',product:1,product_name:product.name,category_names:['长分类'],display_name_cn:'灯具10W24V',sales_model:'F7-1024',parameter_values:{'1:power':'10','1:voltage':'24'},active:true,unit:'pcs',currency:'USD',current_stock:'0',default_price:'99999999.99'}
function gate(){let resolve;const promise=new Promise(r=>{resolve=r});return{promise,resolve}}
// Read-only mock fixture: exercise the real page/editor without backend writes.
async function setup(page) {
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (route.request().method() !== 'GET') return route.fulfill({status:405,json:{detail:'Unexpected write in read-only race test'}})
    const responses = {
      '/api/session/current-operator/': {name:'Isolated developer',development_superadmin:true,has_all_permissions:true},
      '/api/products/': [product],
      '/api/categories/tree/': [{id:1,name:'照明',attributes,effective_attributes:attributes}],
      '/api/suppliers/': [],
      '/api/skus/': [existing,{...existing,id:8,sku:'SKU-OFF',sku_code:'SKU-OFF',display_name_cn:'停用样本',active:false}],
    }
    return route.fulfill({json:responses[path] || []})
  })
}
for(const width of [1440,390])for(const outcome of ['success','failure'])test(`SKU source context race ${outcome} and long content ${width}`,async({page},testInfo)=>{
  await page.setViewportSize({width,height:1000});await setup(page)
  const requests=[]
  await page.route('**/api/supplier-skus/**',async route=>{
    const pending=gate();requests.push({pending,sku:new URL(route.request().url()).searchParams.get('sku')})
    await route.fulfill(await pending.promise)
  })
  await page.goto('/skus')
  await expect(page.locator('.sku-data-row')).toHaveCount(2)
  await page.screenshot({path:testInfo.outputPath(`sku-list-${width}.png`),fullPage:true})
  await page.locator('.sku-data-row').filter({hasText:'SKU-F7'}).getByRole('button',{name:'编辑',exact:true}).click()
  const editor=page.getByRole('dialog',{name:'编辑 SKU',exact:true})
  await expect.poll(()=>requests.length).toBe(1)
  // A non-overflowing half-width stack is still unusable on a phone.
  const basics=editor.locator('.sku-basic-card > .sku-basics')
  const layout=await basics.evaluate(node=>({
    columns:getComputedStyle(node).gridTemplateColumns.split(' ').length,
    contentWidth:node.clientWidth-parseFloat(getComputedStyle(node).paddingLeft)-parseFloat(getComputedStyle(node).paddingRight),
    fields:[...node.querySelectorAll(':scope > .field')].map(field=>({
      width:field.getBoundingClientRect().width,
      controlWidth:field.querySelector('input,select').getBoundingClientRect().width,
    })),
  }))
  if(width===390){
    expect(layout.columns).toBe(1)
    expect(layout.contentWidth).toBeGreaterThan(230)
    for(const field of layout.fields){
      expect(field.width).toBeGreaterThanOrEqual(layout.contentWidth-2)
      expect(field.controlWidth).toBeGreaterThanOrEqual(layout.contentWidth-2)
    }
  }else{
    expect(layout.columns).toBe(6)
  }

  await editor.getByRole('button',{name:'取消',exact:true}).click()
  await expect(editor).toHaveCount(0)
  await page.locator('.sku-data-row').filter({hasText:'SKU-OFF'}).getByRole('button',{name:'编辑',exact:true}).click()
  await expect.poll(()=>requests.length).toBe(2)
  expect(requests.map(r=>r.sku)).toEqual(['7','8'])
  const received=page.waitForResponse(r=>r.url().includes('/supplier-skus/')&&new URL(r.url()).searchParams.get('sku')==='7')
  requests[0].pending.resolve(outcome==='success'
    ? {json:[{id:99,supplier_name:'旧 SKU 来源',supplier_model:'OLD'}]}
    : {status:400,json:{detail:'旧 SKU 来源失败'}})
  await (await received).finished()
  // Let Axios and Vue consume the released response before asserting the pending B state.
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))
  await expect(editor.locator('.supplier-sources-section')).toContainText('加载供应商来源中')
  await expect(editor.locator('.supplier-sources-section')).not.toContainText('旧 SKU 来源')
  await expect(editor.locator('.supplier-sources-section [role="alert"]')).toHaveCount(0)
  requests[1].pending.resolve({json:[{id:88,supplier_name:'当前供应商长名称'.repeat(8),supplier_model:'CURRENT-LONG-MODEL-'.repeat(8),supplier_sku_code:'CURRENT',purchase_price:'12.5',currency:'USD',is_active:true}]})
  await expect(editor.locator('.supplier-sources-section')).toContainText('CURRENT')
  await editor.locator('.supplier-sources-section').scrollIntoViewIfNeeded()
  expect(await editor.locator('.sku-body').evaluate(n=>n.scrollWidth<=n.clientWidth+2)).toBeTruthy()
  await page.screenshot({path:testInfo.outputPath(`sku-editor-${width}.png`),fullPage:true})
  await editor.getByRole('button',{name:'取消',exact:true}).click()
  await page.goto('/products');await expect(page.locator('tbody')).toContainText(product.name)
  await page.screenshot({path:testInfo.outputPath(`products-${width}.png`),fullPage:true})
})
