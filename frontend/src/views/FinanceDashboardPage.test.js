import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const pageUrl = new URL('./FinanceDashboardPage.vue', import.meta.url)

test('finance dashboard keeps book reference and adds confirmed bank cash facts separately', async () => {
  const source = await readFile(pageUrl, 'utf8')
  assert.match(source, /\/actual-rmb-cash\//)
  assert.match(source, /银行实际人民币资金/)
  assert.match(source, /仅统计已登记并人工确认的银行资金事件/)
  assert.match(source, /银行实际净额/)
  assert.match(source, /查看原始事件/)
  assert.match(source, /账面收支（人民币折算参考）/)
})
