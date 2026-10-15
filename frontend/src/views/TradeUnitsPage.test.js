import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./TradeUnitsPage.vue', import.meta.url)

test('trade-unit page preserves deactivate and default-source actions', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /change\(row,\{active:!row.active\}\)/)
  assert.match(source, /change\(row,\{is_default:!row.is_default\}\)/)
  assert.match(source, /名称、单位、换算系数、供应商和小数规则保存后固定。规格变化时请停用旧项后新建/)
})
