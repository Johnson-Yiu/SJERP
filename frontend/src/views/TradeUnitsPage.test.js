import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./TradeUnitsPage.vue', import.meta.url)

test('trade-unit page preserves deactivate and default-source actions', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /change\(row, \{ active: !row.active \}\)/)
  assert.match(source, /change\(row, \{ is_default: true \}\)/)
  assert.match(source, /规格保存后，名称、单位及换算关系固定。变更卷长时停用旧规格并新增/)
})
