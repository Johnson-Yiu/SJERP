import { expect, it } from 'vitest'
import { readFile } from 'node:fs/promises'

const drawers = [
  'src/components/EntityDetailModal.vue',
  'src/components/OrderDetailModal.vue',
  'src/components/QuoteDetailModal.vue',
]

it('all shared detail drawers use the system typography scale', async () => {
  for (const file of drawers) {
    const source = await readFile(file, 'utf8')
    const hardCodedSizes = source.match(/font-size\s*:\s*\d+(?:\.\d+)?px/g) ?? []
    expect(hardCodedSizes).toEqual(
      file === 'src/components/EntityDetailModal.vue' ? ['font-size:13px'] : [],
    )
    expect(source, `${file} needs a page-level drawer title`).toMatch(/\.detail-identity h2\{[^}]*font-size:var\(--text-page\)/)
    expect(source, `${file} needs section headings`).toMatch(/font-size:var\(--text-section\)/)
    expect(source, `${file} needs body typography`).toMatch(/font-size:var\(--text-body\)/)
    expect(source, `${file} needs helper typography`).toMatch(/font-size:var\(--text-caption\)/)
    if (file === 'src/components/EntityDetailModal.vue') {
      expect(source, 'rich text must resolve to body typography').toMatch(/\.info-grid span,\.richtext-view\{font-size:var\(--text-body\)/)
    }
  }
})
