import test from 'node:test'
import assert from 'node:assert/strict'
import { orderTasks } from './orderOverview.js'
const lines={items:[{sku:1,draftable_quantity:2,unshipped_quantity:2}]}
for(const state of ['draft','cancelled','confirmed','production','shipped','completed']) test(`order tasks ${state} debt matrix`,()=>{
 const keys=orderTasks({status:state},lines,{balance_amount:'160'}).map(t=>t.key)
 if(state==='draft')assert.deepEqual(keys,['confirm'])
 else if(state==='cancelled')assert.deepEqual(keys,[])
 else if(state==='completed')assert.deepEqual(keys,['receivable'])
 else {assert.ok(keys.includes('receivable'));assert.equal(keys.includes('shipment'),['confirmed','production'].includes(state));assert.equal(keys.includes('complete'),state==='shipped')}
})
test('completed settled has no tasks, refund dynamically restores only receipt',()=>{
 const order={status:'completed'};const payment={balance_amount:'0'}
 assert.deepEqual(orderTasks(order,lines,payment),[])
 payment.balance_amount='40';assert.deepEqual(orderTasks(order,lines,payment).map(t=>t.key),['receivable'])
})
test('masked, absent and denied financial amounts never fall back to protected order balance',()=>{
 for(const payment of [{balance_amount:null},{}, {balance_amount:'160'}]){
  const tasks=orderTasks({status:'completed',balance_amount:'500'},lines,payment,{canViewPayments:false})
  assert.deepEqual(tasks,[])
 }
 assert.deepEqual(orderTasks({status:'completed',balance_amount:'500'},lines,{balance_amount:null}),[])
})

for(const state of ['no_plans','review']) test(`unknown ${state} is review, never confirmed zero`,()=>{
 const order={status:'completed',total_amount:'500'},payment={balance_amount:'0',settlement:{state}}
 const tasks=orderTasks(order,lines,payment);assert.deepEqual(tasks.map(t=>t.key),['receivable_review']);assert.equal(tasks[0].amount,undefined)
 assert.deepEqual(orderTasks(order,lines,payment,{canViewPayments:false}),[])
 assert.deepEqual(orderTasks({...order,total_amount:'0'},lines,payment),[])
 assert.deepEqual(orderTasks({...order,status:'cancelled'},lines,payment),[])
 assert.deepEqual(orderTasks({...order,status:'draft'},lines,payment).map(t=>t.key),['confirm'])
})
