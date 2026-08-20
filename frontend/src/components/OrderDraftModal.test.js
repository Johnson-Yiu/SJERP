import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const componentUrl = new URL('./OrderDraftModal.vue', import.meta.url)

test('lead-time input reserves room for ten digits', async () => {
  const source = await readFile(componentUrl, 'utf8')

  assert.match(source, /\.lead-time-input>input\{flex:0 0 10ch!important;width:10ch!important/)
})
