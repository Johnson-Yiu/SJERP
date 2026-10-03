import { reactive } from 'vue'

const queue = []
let nextId = 1

export const dialogState = reactive({ current: null, toasts: [] })

function showNext() {
  if (dialogState.current || !queue.length) return
  dialogState.current = queue.shift()
}

function enqueue(kind, options = {}) {
  return new Promise(resolve => {
    queue.push({
      id: nextId++,
      kind,
      title: options.title || (kind === 'input' ? '请输入信息' : kind === 'alert' ? '提示' : '请确认'),
      message: options.message || '',
      label: options.label || '',
      placeholder: options.placeholder || '',
      required: Boolean(options.required),
      maxLength: options.maxLength || 500,
      confirmText: options.confirmText || (kind === 'alert' ? '知道了' : '确认'),
      cancelText: options.cancelText || '取消',
      danger: Boolean(options.danger),
      resolve,
    })
    showNext()
  })
}

export function confirmDialog(options) {
  return enqueue('confirm', options)
}

export function inputDialog(options) {
  return enqueue('input', options)
}

export function alertDialog(options) {
  return enqueue('alert', options)
}

export function resolveDialog(value) {
  const current = dialogState.current
  if (!current) return
  dialogState.current = null
  current.resolve(value)
  queueMicrotask(showNext)
}

export function showToast(message, { error = false, duration = 3200 } = {}) {
  const toast = { id: nextId++, message, error }
  dialogState.toasts.push(toast)
  if (duration > 0) window.setTimeout(() => dismissToast(toast.id), duration)
  return toast.id
}

export function dismissToast(id) {
  const index = dialogState.toasts.findIndex(toast => toast.id === id)
  if (index >= 0) dialogState.toasts.splice(index, 1)
}
