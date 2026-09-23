import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const drawers = [
  'src/components/EntityDetailModal.vue',
  'src/components/OrderDetailModal.vue',
  'src/components/QuoteDetailModal.vue',
]

test('all shared detail drawers use the system typography scale', async () => {
  for (const file of drawers) {
    const source = await readFile(file, 'utf8')
    const hardCodedSizes = source.match(/font-size\s*:\s*\d+(?:\.\d+)?px/g) ?? []
    assert.deepEqual(
      hardCodedSizes,
      file === 'src/components/EntityDetailModal.vue' ? ['font-size:13px'] : [],
      `${file} has an unexpected hard-coded font size`,
    )
    assert.match(source, /\.detail-identity h2\{[^}]*font-size:var\(--text-page\)/, `${file} needs a page-level drawer title`)
    assert.match(source, /font-size:var\(--text-section\)/, `${file} needs section headings`)
    assert.match(source, /font-size:var\(--text-body\)/, `${file} needs body typography`)
    assert.match(source, /font-size:var\(--text-caption\)/, `${file} needs helper typography`)
    if (file === 'src/components/EntityDetailModal.vue') {
      assert.match(source, /\.info-grid span,\.richtext-view\{font-size:var\(--text-body\)/, 'rich text must resolve to body typography')
    }
  }
})
