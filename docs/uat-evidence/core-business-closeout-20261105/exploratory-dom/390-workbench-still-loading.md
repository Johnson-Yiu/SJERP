# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: core-business-closeout.spec.js >> real core closure 390px
- Location: browser-tests\core-business-closeout.spec.js:6:33

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: getByRole('dialog', { name: '订单工作台' }).locator('.payment-card')
Expected substring: "款项已结清"
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toContainText" getByRole('dialog', { name: '订单工作台' }).locator('.payment-card') with timeout 5000ms
  - waiting for getByRole('dialog', { name: '订单工作台' }).locator('.payment-card')

```

```yaml
- complementary:
  - text: S
  - strong: 森爵照明管理系统
  - text: 客户 · 销售 · 产品
  - navigation:
    - text: 经营
    - link "经营概览":
      - /url: /
    - link "报表中心":
      - /url: /reports
    - link "历史订单分析":
      - /url: /historical-orders
    - text: 客户
    - link "客户管理":
      - /url: /customers
    - link "联系人":
      - /url: /contacts
    - link "跟进记录":
      - /url: /follow-ups
    - text: 销售
    - link "报价管理":
      - /url: /quotes
    - link "订单管理":
      - /url: /orders
    - text: 采购与库存
    - link "供应商管理":
      - /url: /suppliers
    - link "采购管理":
      - /url: /purchase-orders
    - link "库存":
      - /url: /inventory
    - link "库存流水":
      - /url: /inventory-movements
    - text: 产品资料
    - link "产品管理":
      - /url: /products
    - link "SKU 管理":
      - /url: /skus
    - link "产品分类":
      - /url: /categories
    - link "产品参数":
      - /url: /product-parameters
    - link "包装管理":
      - /url: /sku-packaging
    - link "交易单位":
      - /url: /sku-trade-units
    - link "产品证书":
      - /url: /product-certificates
    - link "HS 编码维护":
      - /url: /hs-codes
    - text: 财务与工具
    - link "财务概览":
      - /url: /finance
    - link "应收计划":
      - /url: /receivables
    - link "应付计划":
      - /url: /payables
    - link "财务流水":
      - /url: /transactions
    - link "人民币资金":
      - /url: /rmb-cash-events
    - link "账户资金":
      - /url: /finance-ledger
    - link "数据导入":
      - /url: /import
    - link "历史资料承接":
      - /url: /history-takeover
    - text: 组织与系统
    - link "组织与权限":
      - /url: /organization
  - text: J
  - strong: 开发身份：Johnson
  - text: 超级管理员 · 全部功能与数据权限
- main:
  - button
  - text: Sales orders
  - heading "订单管理" [level=1]
  - text: J
  - paragraph: 管理销售订单、履约与回款。
  - button "新建订单"
  - textbox "搜索订单号或客户"
  - combobox "按订单状态筛选":
    - option "全部状态" [selected]
    - option "草稿"
    - option "已确认"
    - option "生产中"
    - option "已发货"
    - option "已完成"
    - option "已取消"
  - combobox "按订单待办筛选":
    - option "全部待办" [selected]
    - option "待出库"
    - option "交期已到"
  - button "重置"
  - status: 正在加载…
  - dialog "订单工作台": 正在加载订单工作台…
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | import fs from 'node:fs'
  3  | import path from 'node:path'
  4  | const root = path.resolve('../docs/uat-evidence/core-business-closeout-20261105/chrome')
  5  | test.use({channel:'chrome'})
  6  | for (const width of [1440,390]) test(`real core closure ${width}px`, async({page})=>{
  7  |  test.setTimeout(120000);fs.mkdirSync(root,{recursive:true})
  8  |  const http=[],errors=[]
  9  |  page.on('pageerror',e=>errors.push(String(e)))
  10 |  page.on('response',r=>{if(r.url().includes('/api/'))http.push({method:r.request().method(),url:r.url(),status:r.status()})})
  11 |  const api=async(url,body,status=201,key)=>{
  12 |   const r=await page.request.post('/api'+url,{data:body,headers:key?{'Idempotency-Key':key}:{}})
  13 |   const text=await r.text();fs.writeFileSync(path.join(root,`${width}-http-in-progress.json`),JSON.stringify({http,last:{url,status:r.status(),request:body,response:text}},null,2));http.push({method:'POST',url,status:r.status(),request:body,response:text})
  14 |   expect(r.status(),text).toBe(status);return JSON.parse(text)
  15 |  }
  16 |  await page.setViewportSize({width,height:1000})
  17 |  const suffix=String(width)
  18 |  const customer=await api('/customers/',{code:'CORE-'+suffix,name:'合成核心客户'+suffix,country:'CN',contacts:[{name:'合成联系人',email:'core@example.test'}]})
  19 |  const category=await api('/categories/',{name:'合成核心分类'+suffix})
  20 |  const supplier=await api('/suppliers/',{code:width===1440?'CD':'CN',name:'合成核心供应商'+suffix,supply_categories:[category.id]})
  21 |  const product=await api('/products/',{code:'CORE-P-'+suffix,name:'合成核心产品'+suffix,category:category.id,sales_model_prefix:'CORE'+suffix})
  22 |  const sku=await api('/skus/',{sku:'CORE-S-'+suffix,product:product.id,unit:'pcs',specification:'6PCS',sales_model:'CORE'+suffix})
  23 |  const day='2026-11-05'
  24 |  const order=await api('/orders/',{customer:customer.id,order_date:day,currency:'CNY',exchange_rate:'1',items:[{sku:sku.id,quantity:'6',unit_price:'10'}]})
  25 |  await api(`/orders/${order.id}/confirm/`,{},200)
  26 |  const po=await api('/purchase-orders/',{supplier:supplier.id,payment_terms_snapshot:[{label:'合成到货付款',ratio:'1',due_basis:'order_date',offset_days:0}],order_date:day,currency:'CNY',exchange_rate:'1',items:[{sku:sku.id,quantity:'6',unit_price:'3'}]})
  27 |  await api(`/purchase-orders/${po.id}/place/`,{},200)
  28 |  await page.goto(`/purchase-orders?detail=${po.id}`)
  29 |  const purchase=page.getByRole('dialog',{name:'采购工作台'})
  30 |  await expect(purchase).toBeVisible()
  31 |  await purchase.getByRole('button',{name:/到货.*入库|验货.*入库|收货/}).first().click()
  32 |  await purchase.getByRole('button',{name:'验货入库',exact:true}).first().click()
  33 |  const receipt=page.getByRole('dialog',{name:'验货合格入库'})
  34 |  await expect(receipt).toBeVisible()
  35 |  await receipt.getByRole('checkbox',{name:'已核对型号、数量及外观，仅登记合格品'}).check()
  36 |  await page.screenshot({path:path.join(root,`${width}-receipt-before.png`),fullPage:true})
  37 |  await receipt.getByRole('button',{name:/确认.*入库/}).click()
  38 |  await expect(receipt).toBeHidden()
  39 |  await expect(page.getByText('验货入库已完成，库存、预留及在途数量已同步。')).toBeVisible()
  40 |  await expect(purchase.locator('.receipt-heading')).toContainText('已到 6.00')
  41 |  await expect(purchase.locator('.receipt-history-row')).toHaveCount(1)
  42 |  await expect(purchase.locator('header').first()).toContainText('已完成')
  43 |  await page.screenshot({path:path.join(root,`${width}-receipt-after.png`),fullPage:true})
  44 |  const detail=await page.request.get(`/api/orders/${order.id}/`);const saved=await detail.json()
  45 |  const ship={shipment_date:day,items:[{order_item:saved.items[0].id,quantity:'6'}]}
  46 |  await api(`/orders/${order.id}/ship/`,ship,201,'CHROME-'+suffix)
  47 |  await page.goto(`/orders?detail=${order.id}`)
  48 |  const modal=page.getByRole('dialog',{name:'订单工作台'})
  49 |  await expect(modal).toBeVisible()
  50 |  await modal.getByRole('button',{name:'完成履约',exact:true}).first().click()
  51 |  const confirm=page.getByTestId('dialog-confirm')
  52 |  if(await confirm.isVisible()) await confirm.click()
  53 |  await expect(modal).toContainText('履约：已完成')
  54 |  await expect(modal.locator('.current-todo-card')).toContainText('60.00')
  55 |  await page.screenshot({path:path.join(root,`${width}-completed-debt.png`),fullPage:true})
  56 |  const money=(amount,kind)=>api('/transactions/',{order:order.id,transaction_date:day,amount,currency:'CNY',exchange_rate:'1',kind,direction:kind==='refund'?'expense':'income',category:kind==='refund'?'合成退款':'客户收款'})
  57 |  await money('60','customer_receipt');await page.reload()
> 58 |  await expect(modal.locator('.payment-card')).toContainText('款项已结清')
     |                                               ^ Error: expect(locator).toContainText(expected) failed
  59 |  await money('10','refund');await page.reload()
  60 |  await expect(modal).toContainText('履约：已完成')
  61 |  await expect(modal.locator('.current-todo-card')).toContainText('10.00')
  62 |  await page.screenshot({path:path.join(root,`${width}-refund-todo.png`),fullPage:true})
  63 |  expect(errors).toEqual([])
  64 |  fs.writeFileSync(path.join(root,`${width}-http.json`),JSON.stringify({browser:await page.context().browser().version(),width,http,errors},null,2))
  65 | })
  66 |
```
