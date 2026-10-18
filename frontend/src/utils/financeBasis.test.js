import test from 'node:test'
import assert from 'node:assert/strict'
import {resolveBlock} from '../reports/registry.js'
import {BOOK_RMB_NOTE} from './financeBasis.js'
test('legacy cash block IDs and custom configurations retain their query contract',()=>{
 const config={title:'旧自定义净现金流',date_field:'transaction_date',grain:'quarter',filters:{filter_currency:'CNY'}}
 const original=structuredClone(config)
 assert.deepEqual(resolveBlock('cash-trend',config),{source:'cash',group_by:'time',grain:'quarter',metric:'amount',view:'line',...config})
 assert.deepEqual(config,original);assert.equal(resolveBlock('cash-category').source,'cash')
 assert.ok(BOOK_RMB_NOTE.includes('原币为CNY'));assert.ok(BOOK_RMB_NOTE.includes('不代表银行实际到账'))
})
