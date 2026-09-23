import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('resource payload serializes empty optional dates as null', async () => {
  const source = await readFile(new URL('./ResourcePage.vue', import.meta.url), 'utf8')

  assert.match(source, /if \(type === 'date' && value === ''\) value = null/)
})
