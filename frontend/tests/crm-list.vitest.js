import { describe, expect, it } from 'vitest'
import { contactRows, duplicateContactHint, followUpRows, richTextExcerpt } from '../src/utils/crmList.js'

const contacts = [
  { id: 1, customer: 10, name: 'Lin Yu', email: 'lin@example.test', phone: '+86 123', is_primary: true },
  { id: 2, customer: 10, name: 'Mei Chen', email: 'mei@example.test', phone: '+86 456', is_primary: false },
  { id: 3, customer: 20, name: 'Lin Yu', email: 'other@example.test', phone: '+86 789', is_primary: true },
]

describe('CRM list presentation helpers', () => {
  it('filters contacts by customer and primary status without mutating source rows', () => {
    expect(contactRows(contacts, { customer: '10', primary: 'primary' }).map(row => row.id)).toEqual([1])
    expect(contactRows(contacts, { customer: '10', primary: 'other' }).map(row => row.id)).toEqual([2])
    expect(contactRows(contacts, { search: 'EXAMPLE.TEST' }).map(row => row.id)).toEqual([1, 2, 3])
    expect(contactRows(contacts, { search: 'lin' }).map(row => row.id)).toEqual([1, 3])
    expect(contacts).toHaveLength(3)
  })

  it('filters and sorts follow-ups by customer, method, local date range and selected order', () => {
    const rows = [
      { id: 1, customer: 10, type: 'phone', followed_at: '2026-10-12T09:00:00+08:00' },
      { id: 2, customer: 10, type: 'email', followed_at: '2026-10-14T09:00:00+08:00' },
      { id: 3, customer: 20, type: 'phone', followed_at: '2026-10-13T09:00:00+08:00' },
    ]
    rows[0].owner = '林晓'
    rows[1].owner = '陈宁'
    expect(followUpRows(rows, { customer: '10', owner: '林晓', type: 'phone', from: '2026-10-12', to: '2026-10-13' }).map(row => row.id)).toEqual([1])
    expect(followUpRows(rows, { customer: '10', sort: 'oldest' }).map(row => row.id)).toEqual([1, 2])
    expect(followUpRows(rows, { customer: '10' }).map(row => row.id)).toEqual([2, 1])
    expect(rows.map(row => row.id)).toEqual([1, 2, 3])
  })

  it('shows possible duplicate contacts as a non-blocking advisory scoped to one customer', () => {
    expect(duplicateContactHint(contacts, { customer: 10, name: ' lin yu ' }, 99)).toContain('Lin Yu')
    expect(duplicateContactHint(contacts, { customer: 20, name: 'Mei Chen' }, 99)).toBe('')
    expect(duplicateContactHint(contacts, { customer: 10, email: 'MEI@example.test' }, 2)).toBe('')
  })

  it('creates plain excerpts from rich-text markup and bounds long content', () => {
    expect(richTextExcerpt('<p>第一段</p><p><strong>第二段</strong> &amp; 回复</p>')).toBe('第一段 第二段 & 回复')
    expect(richTextExcerpt('长文本'.repeat(40), 20)).toBe(`${'长文本'.repeat(40).slice(0, 20)}…`)
  })
})
