import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import AppDialogHost from '../src/components/AppDialogHost.vue'
import { alertDialog, confirmDialog, dialogState, inputDialog, showToast } from '../src/dialogs'

const settle = () => new Promise(resolve => setTimeout(resolve, 0))
const element = selector => document.querySelector(selector)
const mounted = []
const mountHost = () => { const wrapper = mount(AppDialogHost); mounted.push(wrapper); return wrapper }

afterEach(() => {
  mounted.splice(0).forEach(wrapper => wrapper.unmount())
  dialogState.current = null
  dialogState.toasts.splice(0)
  vi.restoreAllMocks()
})

describe('app-owned dialogs', () => {
  it('returns false from Cancel and true from Confirm', async () => {
    const wrapper = mountHost()
    const cancelled = confirmDialog({ title: '确认删除', message: '删除后无法恢复。', danger: true })
    await nextTick()
    element('[data-testid="dialog-cancel"]').click()
    await nextTick()
    await expect(cancelled).resolves.toBe(false)

    const confirmed = confirmDialog({ title: '确认删除', message: '删除后无法恢复。', danger: true })
    await nextTick()
    element('[data-testid="dialog-confirm"]').click()
    await expect(confirmed).resolves.toBe(true)
  })

  it('disables confirmation while it is resolving, preventing double submission', async () => {
    const wrapper = mountHost()
    const confirmed = confirmDialog({ title: '确认操作', message: '继续吗？' })
    await nextTick()
    const button = element('[data-testid="dialog-confirm"]')
    button.click()
    button.click()
    await nextTick()
    expect(button.disabled).toBe(true)
    await settle()
    await expect(confirmed).resolves.toBe(true)
  })

  it('validates required input, returns its value, and returns null on Cancel', async () => {
    const wrapper = mountHost()
    const required = inputDialog({ title: '填写原因', label: '原因', required: true })
    await nextTick()
    expect(element('[data-testid="dialog-confirm"]').disabled).toBe(true)
    const input = element('[data-testid="dialog-input"]')
    input.value = '采购计划变更'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    await nextTick()
    element('[data-testid="dialog-confirm"]').click()
    await expect(required).resolves.toBe('采购计划变更')

    const cancelled = inputDialog({ title: '填写原因', required: true })
    await nextTick()
    element('[data-testid="dialog-cancel"]').click()
    await nextTick()
    await expect(cancelled).resolves.toBeNull()
  })

  it('shows an app-owned alert and a dismissible toast', async () => {
    const wrapper = mountHost()
    const alert = alertDialog({ title: '操作提示', message: '请检查输入。' })
    await nextTick()
    expect(document.body.textContent).toContain('请检查输入。')
    element('[data-testid="dialog-confirm"]').click()
    await expect(alert).resolves.toBe(true)

    showToast('保存成功', { duration: 0 })
    await nextTick()
    expect(document.body.textContent).toContain('保存成功')
    element('[aria-label="关闭提示"]').click()
    await nextTick()
    expect(document.body.textContent).not.toContain('保存成功')
  })
})
