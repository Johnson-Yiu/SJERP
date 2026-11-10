import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { syntheticVoucherPdf } from './helpers/bank-voucher.js'
const root = process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT
 ? path.join(process.env.ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT, 'browser', 'core-business-closeout')
 : path.resolve('../docs/uat-evidence/core-business-closeout-20261105/chrome')
test.use({channel:'chrome'})
for (const width of [1440,390]) test(`real core closure ${width}px`, async({page})=>{
 test.setTimeout(120000);fs.mkdirSync(root,{recursive:true})
 const http=[],errors=[]
 page.on('pageerror',e=>errors.push(String(e)))
 page.on('response',r=>{if(r.url().includes('/api/'))http.push({method:r.request().method(),url:r.url(),status:r.status()})})
 const api=async(url,body,status=201,key)=>{
  const r=await page.request.post('/api'+url,{data:body,headers:key?{'Idempotency-Key':key}:{}})
  const text=await r.text();fs.writeFileSync(path.join(root,`${width}-http-in-progress.json`),JSON.stringify({http,last:{url,status:r.status(),request:body,response:text}},null,2));http.push({method:'POST',url,status:r.status(),request:body,response:text})
  expect(r.status(),text).toBe(status);return JSON.parse(text)
 }
 await page.setViewportSize({width,height:1000})
 const suffix=String(width)
 const customer=await api('/customers/',{code:'CORE-'+suffix,name:'合成核心客户'+suffix,country:'CN',contacts:[{name:'合成联系人',email:'core@example.test'}]})
 const category=await api('/categories/',{name:'合成核心分类'+suffix})
 const supplier=await api('/suppliers/',{code:width===1440?'CD':'CN',name:'合成核心供应商'+suffix,supply_categories:[category.id]})
 const product=await api('/products/',{code:'CORE-P-'+suffix,name:'合成核心产品'+suffix,category:category.id,sales_model_prefix:'CORE'+suffix})
 const sku=await api('/skus/',{sku:'CORE-S-'+suffix,product:product.id,unit:'pcs',specification:'6PCS',sales_model:'CORE'+suffix})
 const day='2026-11-05'
 const order=await api('/orders/',{customer:customer.id,order_date:day,currency:'CNY',exchange_rate:'1',items:[{sku:sku.id,quantity:'6',unit_price:'10'}]})
 await api(`/orders/${order.id}/confirm/`,{},200)
 const po=await api('/purchase-orders/',{supplier:supplier.id,payment_terms_snapshot:[{label:'合成到货付款',ratio:'1',due_basis:'order_date',offset_days:0}],order_date:day,currency:'CNY',exchange_rate:'1',items:[{sku:sku.id,quantity:'6',unit_price:'3'}]})
 await api(`/purchase-orders/${po.id}/place/`,{},200)
 await page.goto(`/purchase-orders?detail=${po.id}`)
 const purchase=page.getByRole('dialog',{name:'采购工作台'})
 await expect(purchase).toBeVisible()
 await purchase.getByRole('button',{name:/到货.*入库|验货.*入库|收货/}).first().click()
 await purchase.getByRole('button',{name:'验货入库',exact:true}).first().click()
 const receipt=page.getByRole('dialog',{name:'验货合格入库'})
 await expect(receipt).toBeVisible()
 await receipt.getByRole('checkbox',{name:'已核对型号、数量及外观，仅登记合格品'}).check()
 await page.screenshot({path:path.join(root,`${width}-receipt-before.png`),fullPage:true})
 await receipt.getByRole('button',{name:/确认.*入库/}).click()
 await expect(receipt).toBeHidden()
 await expect(page.getByText('验货入库已完成，库存、预留及在途数量已同步。')).toBeVisible()
 await expect(purchase.locator('.receipt-heading')).toContainText('已到 6.00')
 await expect(purchase.locator('.receipt-history-row')).toHaveCount(1)
 await expect(purchase.locator('header').first()).toContainText('已完成')
 await page.screenshot({path:path.join(root,`${width}-receipt-after.png`),fullPage:true})
 await purchase.getByRole('button',{name:'供应商应付',exact:true}).click()
 await purchase.getByRole('button',{name:'登记付款',exact:true}).click()
 const payment=page.getByRole('dialog',{name:'登记付款',exact:true})
 await payment.getByPlaceholder('请输入付款金额').fill('6')
 await payment.getByPlaceholder('填写转账流水号（可选）').fill('合成核心验收参考号')
 await page.screenshot({path:path.join(root,`${width}-supplier-pay-before.png`),fullPage:true})
 const paymentResult=page.waitForResponse(r=>new URL(r.url()).pathname===`/api/purchase-orders/${po.id}/pay/`)
 await payment.getByRole('button',{name:'确认登记付款',exact:true}).click()
 const paid=await paymentResult;expect(paid.status()).toBe(201)
 http.push({method:'POST',url:paid.url(),status:paid.status(),body:await paid.json()})
 await expect(payment).toBeHidden()
 await expect(purchase.locator('.summary-grid>div').filter({hasText:'未付'})).toContainText('12.00')
 await page.screenshot({path:path.join(root,`${width}-supplier-pay-after.png`),fullPage:true})

 const detail=await page.request.get(`/api/orders/${order.id}/`);const saved=await detail.json()
 const ship={shipment_date:day,items:[{order_item:saved.items[0].id,quantity:'6'}]}
 await api(`/orders/${order.id}/ship/`,ship,201,'CHROME-'+suffix)
 await page.goto(`/orders?detail=${order.id}`)
 const modal=page.getByRole('dialog',{name:'订单工作台'})
 await expect(modal).toBeVisible()
 await modal.getByRole('button',{name:'完成履约',exact:true}).first().click()
 const confirm=page.getByTestId('dialog-confirm')
 if(await confirm.isVisible()) await confirm.click()
 await expect(modal).toContainText('履约：已完成')
 await expect(modal.locator('.current-todo-card')).toContainText('60.00')
 await page.screenshot({path:path.join(root,`${width}-completed-debt.png`),fullPage:true})
 const reloadOrder=async()=>{
  const [response]=await Promise.all([page.waitForResponse(r=>new URL(r.url()).pathname===`/api/orders/${order.id}/workbench/`),page.reload()])
  expect(response.status()).toBe(200);http.push({method:'GET',url:response.url(),status:response.status(),body:await response.json()})
 }
 const receiptData = {order:order.id,transaction_date:day,amount:'60',currency:'CNY',exchange_rate:'1',kind:'customer_receipt',direction:'income',category:'客户收款'}
 const receiptKey = 'CORE-RECEIPT-'+suffix
 const receiptTransaction = await api('/transactions/',receiptData,201,receiptKey)
 const replay = await api('/transactions/',receiptData,201,receiptKey)
 expect(replay.id).toBe(receiptTransaction.id)
 await reloadOrder()
 await expect(modal.locator('.payment-card')).toContainText('款项已结清')
 const voucher = await page.request.post('/api/transactions/voucher-upload/', {
  multipart: {file: {name: 'synthetic-core-refund.pdf',mimeType:'application/pdf',buffer:syntheticVoucherPdf()}},
 })
 expect(voucher.status()).toBe(201)
 const proof = await voucher.json()
 const refund = await api('/transactions/'+receiptTransaction.id+'/refund-cash/', {
  order:order.id,amount:'10',reason:'合成核心验收退款',voucher:proof.id,actual_date:day,
 },201,'CORE-REFUND-'+suffix)
 expect(refund.refunds).toHaveLength(1)
 expect(Number(refund.refunds[0].amount)).toBe(10)
 expect(refund.refunds[0].actual_date).toBe(day)
 await reloadOrder()
 await expect(modal).toContainText('履约：已完成')
 await expect(modal.locator('.current-todo-card')).toContainText('10.00')
 await page.screenshot({path:path.join(root,`${width}-refund-todo.png`),fullPage:true})
 expect(errors).toEqual([])
 fs.writeFileSync(path.join(root,`${width}-http.json`),JSON.stringify({browser:await page.context().browser().version(),width,http,errors},null,2))
})
