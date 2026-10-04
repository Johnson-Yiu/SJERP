import { describe, expect, it, vi } from 'vitest'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { resourceConfigs } from '../src/resourceConfigs.js'
import { confirmAndDeleteSavedFollowUpAttachment } from '../src/utils/followUpAttachments.js'
import { renderRichText } from '../src/utils/richText.js'

describe('FollowUp rich text display protocol', () => {
  it('renders bold markers as strong elements', () => {
    const html = renderRichText('**加粗**')
    expect(html).toContain('<strong>加粗</strong>')
    expect(html).not.toContain('**')
  })

  it('renders italic markers as emphasis elements', () => {
    const html = renderRichText('_斜体_')
    expect(html).toContain('<em>斜体</em>')
    expect(html).not.toContain('_斜体_')
  })

  it('renders consecutive unordered list lines as ul and li', () => {
    expect(renderRichText('- A\n- B')).toContain('<ul><li>A</li><li>B</li></ul>')
  })

  it('renders consecutive ordered list lines as ol and li', () => {
    expect(renderRichText('1. A\n2. B')).toContain('<ol><li>A</li><li>B</li></ol>')
  })

  it('escapes user HTML and rejects executable image URLs', () => {
    const html = renderRichText('普通：< > &\n<script>window.richTextPwned = true</script>\n![x](javascript:alert(1))')
    const container = document.createElement('div')
    container.innerHTML = html

    expect(html).toContain('&lt; &gt; &amp;')
    expect(container.querySelector('script, iframe, img')).toBeNull()
    expect(container.textContent).toContain('<script>window.richTextPwned = true</script>')
    expect(window.richTextPwned).toBeUndefined()
  })

  it('keeps markdown image display safe and attribute-escaped', () => {
    const html = renderRichText('![clipboard](/media/follow-up-attachments/2026/10/clipboard.png)\n![x](https://example.test/x"onerror=alert(1))')
    const container = document.createElement('div')
    container.innerHTML = html
    const images = [...container.querySelectorAll('img')]

    expect(images).toHaveLength(2)
    expect(images[0].getAttribute('src')).toBe('/media/follow-up-attachments/2026/10/clipboard.png')
    expect(images[0].getAttribute('alt')).toBe('clipboard')
    expect(images.every(image => !image.hasAttribute('onerror'))).toBe(true)
    expect(html).toContain('loading="lazy"')
  })

  it('uses the same rich text renderer for FollowUp content and result', async () => {
    const contentField = resourceConfigs['follow-ups'].fields.find(field => field[0] === 'content')
    const resultField = resourceConfigs['follow-ups'].fields.find(field => field[0] === 'result')
    const detail = await readFile(resolve(process.cwd(), 'src/components/EntityDetailModal.vue'), 'utf8')

    expect(contentField?.[2]).toBe('richtext')
    expect(resultField?.[2]).toBe('richtext')
    expect(detail).toMatch(/renderRichText as richText/)
    expect(detail).toMatch(/richText\(followUpInfo\['跟进记录 \/ 解决方案'\]\)/)
    expect(detail).toMatch(/richText\(followUpInfo\['客户回复 \/ 客户疑问'\]/)
  })
})

describe('saved and pending FollowUp attachments', () => {
  const attachment = { id: 81, name: 'README.md', size: 12 }

  it('does not call DELETE when the app confirmation is cancelled', async () => {
    const api = { delete: vi.fn() }
    const confirmDialog = vi.fn().mockResolvedValue(false)
    const onDeleted = vi.fn()

    await expect(confirmAndDeleteSavedFollowUpAttachment({
      followUpId: 9, attachment, api, confirmDialog, onDeleted,
    })).resolves.toBe(false)

    expect(confirmDialog).toHaveBeenCalledWith(expect.objectContaining({
      title: '删除附件', confirmText: '确认删除', cancelText: '取消',
      message: expect.stringContaining('附件删除将立即生效'),
    }))
    expect(api.delete).not.toHaveBeenCalled()
    expect(onDeleted).not.toHaveBeenCalled()
  })

  it('calls the existing attachment endpoint and removes it only after success', async () => {
    const api = { delete: vi.fn().mockResolvedValue({ status: 204 }) }
    const confirmDialog = vi.fn().mockResolvedValue(true)
    const saved = [attachment, { id: 82, name: 'A.png' }]
    const onDeleted = vi.fn(item => { saved.splice(saved.indexOf(item), 1) })

    await expect(confirmAndDeleteSavedFollowUpAttachment({
      followUpId: 9, attachment, api, confirmDialog, onDeleted,
    })).resolves.toBe(true)

    expect(api.delete).toHaveBeenCalledOnce()
    expect(api.delete).toHaveBeenCalledWith('/follow-ups/9/attachments/81/')
    expect(saved.map(item => item.name)).toEqual(['A.png'])
  })

  it('keeps the saved attachment when DELETE fails and surfaces the error', async () => {
    const failure = new Error('删除失败，请重试')
    const api = { delete: vi.fn().mockRejectedValue(failure) }
    const confirmDialog = vi.fn().mockResolvedValue(true)
    const saved = [attachment]
    const onDeleted = vi.fn(item => { saved.splice(saved.indexOf(item), 1) })
    const onError = vi.fn()

    await expect(confirmAndDeleteSavedFollowUpAttachment({
      followUpId: 9, attachment, api, confirmDialog, onDeleted, onError,
    })).resolves.toBe(false)

    expect(saved).toEqual([attachment])
    expect(onDeleted).not.toHaveBeenCalled()
    expect(onError).toHaveBeenCalledWith(failure)
  })

  it('keeps pending removal local and labels saved attachments separately', async () => {
    const page = await readFile(resolve(process.cwd(), 'src/views/ResourcePage.vue'), 'utf8')
    const pendingRemove = page.match(/function removePendingFollowUpFile\(index\) \{[^}]+\}/)?.[0]

    expect(page).toContain('已保存附件')
    expect(page).toContain('待上传附件')
    expect(page).toMatch(/删除已保存附件 \$\{attachment\.name\}.*deleteSavedFollowUpAttachment\(attachment\)/s)
    expect(page).toMatch(/aria-label="移除待上传附件"[^>]*@click="removePendingFollowUpFile\(index\)"/)
    expect(pendingRemove).toBe('function removePendingFollowUpFile(index) { pendingFollowUpFiles.value.splice(index, 1) }')
    expect(pendingRemove).not.toMatch(/api\.delete/)
  })
})
