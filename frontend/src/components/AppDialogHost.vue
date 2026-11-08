<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { dialogState, dismissToast, resolveDialog } from '../dialogs'

const input = ref('')
const inputElement = ref(null)
const confirming = ref(false)

watch(() => dialogState.current?.id, async () => {
  input.value = ''
  confirming.value = false
  await nextTick()
  inputElement.value?.focus()
})

function cancel() {
  const dialog = dialogState.current
  if (!dialog || confirming.value || dialog.kind === 'alert') return
  resolveDialog(dialog.kind === 'input' ? null : false)
}

function confirm() {
  const dialog = dialogState.current
  if (!dialog || confirming.value) return
  const value = input.value.trim()
  if (dialog.kind === 'input' && dialog.required && !value) {
    inputElement.value?.focus()
    return
  }
  confirming.value = true
  // Leave the disabled state visible for one event-loop turn. Apart from giving
  // feedback, this makes a fast double click unable to resolve the dialog twice.
  window.setTimeout(() => {
    if (dialogState.current?.id === dialog.id) resolveDialog(dialog.kind === 'input' ? value : true)
  }, 0)
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    cancel()
  }
}

window.addEventListener('keydown', onKeydown)
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div v-if="dialogState.current" class="app-dialog-backdrop">
      <section class="app-dialog" role="dialog" aria-modal="true" :aria-labelledby="`app-dialog-title-${dialogState.current.id}`" :aria-describedby="dialogState.current.message ? `app-dialog-message-${dialogState.current.id}` : undefined">
        <header><h2 :id="`app-dialog-title-${dialogState.current.id}`">{{ dialogState.current.title }}</h2></header>
        <div class="app-dialog-body">
          <p v-if="dialogState.current.message" :id="`app-dialog-message-${dialogState.current.id}`">{{ dialogState.current.message }}</p>
          <label v-if="dialogState.current.kind === 'input'" class="app-dialog-input-label">
            <span>{{ dialogState.current.label || '内容' }}<em v-if="dialogState.current.required">*</em></span>
            <textarea ref="inputElement" v-model="input" :placeholder="dialogState.current.placeholder" :maxlength="dialogState.current.maxLength" :required="dialogState.current.required" rows="4" data-testid="dialog-input" @keydown.ctrl.enter.prevent="confirm" />
          </label>
        </div>
        <footer>
          <button v-if="dialogState.current.kind !== 'alert'" type="button" class="btn btn-secondary" data-testid="dialog-cancel" :disabled="confirming" @click="cancel">{{ dialogState.current.cancelText }}</button>
          <button type="button" class="btn" :class="dialogState.current.danger ? 'app-dialog-danger' : 'btn-primary'" data-testid="dialog-confirm" :disabled="confirming || (dialogState.current.kind === 'input' && dialogState.current.required && !input.trim())" @click="confirm">{{ confirming ? '处理中…' : dialogState.current.confirmText }}</button>
        </footer>
      </section>
    </div>
    <div class="app-toast-stack" aria-live="polite" aria-atomic="true">
      <div v-for="toast in dialogState.toasts" :key="toast.id" class="app-toast" :class="{ error: toast.error }" role="status">
        <span>{{ toast.message }}</span><button type="button" aria-label="关闭提示" @click="dismissToast(toast.id)">×</button>
      </div>
    </div>
  </Teleport>
</template>
