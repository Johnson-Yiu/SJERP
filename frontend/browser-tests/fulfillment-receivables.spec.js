import { test, expect } from '@playwright/test'
// MOCKED_TEST: controlled state and permission/failure fixtures; real DB evidence is separate.
async function setup(page,{restricted=false,shipped=false}={}){
 const state={status:shipped?'shipped':'completed',balance:'160.00',paid:'340.00',label:'部分收款',writes:0,fail:false}
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname
  const order={id:7,order_no:'FUP02-500',status:state.status,status_display:state.status==='completed'?'已完成':'已发货',customer_name:'合成客户',currency:'USD',total_amount:'500.00',balance_amount:state.balance,paid_amount:state.paid,items:[]}
  if(path==='/api/session/current-operator/')return route.fulfill({json:restricted?{rbac_enforcement:true,permissions:{orders:{view:true,update:true}}}:{development_superadmin:true,has_all_permissions:true}})
  if(path==='/api/orders/')return route.fulfill({json:[order]})
  if(path==='/api/orders/7/workbench/')return route.fulfill(state.fail?{status:500,json:{detail:'读取失败'}}:{json:{order,items:[],payments:[],inventory:[],plans:[],fulfillment_summary:{},payment_summary:{paid_amount:state.paid,balance_amount:state.balance,planned_amount:'500',settlement:{state:Number(state.balance)?'partial':'settled',label:state.label,overdue_amount:state.balance}}}})
  if(path==='/api/orders/7/fulfillment/')return route.fulfill({json:{items:[],shipments:[]}})
  if(path==='/api/orders/7/')return route.fulfill({json:order})
  if(path==='/api/payment-plans/')return route.fulfill({json:Number(state.balance)?[{id:8,order:7,contract_no:'FUP02-500',counterparty_name:'合成客户',direction:'receivable',currency:'USD',planned_amount:'350',settled_amount:'190',remaining_amount:state.balance,status:'open',is_overdue:true}]:[]})
  if(path==='/api/orders/7/complete/'){
   state.writes++;await state.gate;state.status='completed';return route.fulfill({json:{...order,status:'completed'}})
  }
  return route.fulfill({json:[]})
 })
 await page.goto('/orders?detail=7');return state
}
test('completed receivable navigation, Back, settlement and refund reloads retain fulfillment',async({page})=>{
 const state=await setup(page);const modal=page.getByRole('dialog',{name:'订单工作台'})
 await expect(modal).toContainText('履约：已完成');await expect(modal.locator('.current-todo-card')).toContainText('待收 USD 160.00')
 await modal.locator('.current-todo-card a').click();await expect(page).toHaveURL(/receivables\?order=7/)
 await expect(page.getByRole('table')).toContainText('160.00');await page.goBack()
 await expect(modal.locator('.current-todo-card')).toContainText('160.00')
 state.paid='500.00';state.balance='0.00';state.label='款项已结清';await page.reload()
 await expect(modal.locator('.payment-card')).toContainText('款项已结清');await expect(modal.locator('.current-todo-card a')).toHaveCount(0)
 state.paid='460.00';state.balance='40.00';state.label='部分收款';await page.reload()
 await expect(modal.locator('.current-todo-card')).toContainText('待收 USD 40.00');await expect(modal).toContainText('履约：已完成')
})
test('restricted user cannot read protected debt from malicious unmasked order payload',async({page})=>{
 await setup(page,{restricted:true});const modal=page.getByRole('dialog',{name:'订单工作台'})
 await expect(modal).toContainText('履约：已完成');await expect(modal.locator('.payment-card')).toHaveCount(0)
 await expect(modal.locator('.current-todo-card')).not.toContainText('160');await expect(page.getByRole('columnheader',{name:'已收 / 待收'})).toHaveCount(0)
})
test('completion pending prevents duplicate UI action and failed reload retries without false financial success',async({page})=>{
 const state=await setup(page,{shipped:true});let release;state.gate=new Promise(resolve=>{release=resolve})
 const modal=page.getByRole('dialog',{name:'订单工作台'});const button=modal.getByRole('button',{name:'完成履约',exact:true}).first()
 await button.click();await expect(button).toBeDisabled();await modal.getByRole('button',{name:'完成履约',exact:true}).last().click({force:true});expect(state.writes).toBe(1)
 release();await expect(modal).toContainText('履约：已完成');await expect(modal).toContainText('履约已完成，未收款项继续保留。')
 state.fail=true;await page.reload();await expect(modal).toContainText('加载失败',{timeout:15000});await expect(modal.locator('.payment-card')).toHaveCount(0)
 state.fail=false;await modal.getByRole('button',{name:'重试',exact:true}).click();await expect(modal.locator('.current-todo-card')).toContainText('160.00')
})

