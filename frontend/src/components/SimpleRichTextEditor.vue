<script setup>
import { nextTick, ref } from 'vue'
import { Bold, Italic, List, ListOrdered } from 'lucide-vue-next'

const props = defineProps({ modelValue: { type: String, default: '' }, label: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])
const editor = ref(null)

function replaceSelection(replacement, selectionStart, selectionEnd) {
  const element = editor.value
  element.setRangeText(replacement, element.selectionStart, element.selectionEnd, 'end')
  emit('update:modelValue', element.value)
  nextTick(() => { element.focus(); element.setSelectionRange(selectionStart, selectionEnd) })
}
function inline(marker) {
  const element = editor.value
  const selected = element.value.slice(element.selectionStart, element.selectionEnd) || '文字'
  const start = element.selectionStart + marker.length
  replaceSelection(`${marker}${selected}${marker}`, start, start + selected.length)
}
function list(ordered = false) {
  const element = editor.value
  const selected = element.value.slice(element.selectionStart, element.selectionEnd) || '列表项'
  const lines = selected.split('\n').map((line, index) => `${ordered ? `${index + 1}.` : '-'} ${line}`).join('\n')
  replaceSelection(lines, element.selectionStart, element.selectionStart + lines.length)
}
function readAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}
async function onPaste(event) {
  const files = Array.from(event.clipboardData?.items || [])
    .filter(item => item.kind === 'file')
    .map(item => item.getAsFile())
    .filter(Boolean)
  if (!files.length) return
  event.preventDefault()
  emit('paste-files', files)
  const images = files.filter(file => file.type.startsWith('image/'))
  if (!images.length || !editor.value) return
  const element = editor.value
  const start = element.selectionStart
  const end = element.selectionEnd
  const imageMarkdown = (await Promise.all(images.map(async file => {
    const alt = file.name.replace(/[\[\]()*]/g, ' ').trim() || '粘贴图片'
    return `![${alt}](${await readAsDataUrl(file)})`
  }))).join('\n')
  element.focus()
  element.setRangeText(imageMarkdown, start, end, 'end')
  emit('update:modelValue', element.value)
}
</script>

<template>
  <div class="simple-editor">
    <div class="simple-editor-toolbar" aria-label="简单格式工具栏">
      <button type="button" aria-label="加粗" title="加粗" @mousedown.prevent @click="inline('**')"><Bold :size="14" /></button>
      <button type="button" aria-label="斜体" title="斜体" @mousedown.prevent @click="inline('_')"><Italic :size="14" /></button>
      <button type="button" aria-label="项目列表" title="项目列表" @mousedown.prevent @click="list(false)"><List :size="14" /></button>
      <button type="button" aria-label="编号列表" title="编号列表" @mousedown.prevent @click="list(true)"><ListOrdered :size="14" /></button>
    <span>支持加粗、斜体、列表，并可粘贴图片和附件</span>
  </div>
    <textarea ref="editor" :aria-label="label || undefined" :value="props.modelValue" @input="emit('update:modelValue', $event.target.value)" @paste="onPaste" />
  </div>
</template>

<style scoped>
.simple-editor{border:1px solid #dce3df;border-radius:8px;background:white;overflow:hidden;transition:.15s}.simple-editor:focus-within{border-color:#83ad9f;box-shadow:0 0 0 3px #e2efeb}.simple-editor-toolbar{height:34px;display:flex;align-items:center;gap:3px;padding:0 7px;border-bottom:1px solid #e5eae7;background:#f7f9f7}.simple-editor-toolbar button{width:27px;height:26px;border:0;border-radius:5px;background:transparent;color:#60716b;display:grid;place-items:center}.simple-editor-toolbar button:hover{background:#e6efeb;color:#174f42}.simple-editor-toolbar span{margin-left:auto;color:#98a39f;font-size:var(--text-caption);white-space:nowrap}.simple-editor textarea{display:block;width:100%;min-height:132px;border:0;resize:vertical;padding:10px 11px;outline:0;font-size:var(--text-body);line-height:1.65;color:#20352e;background:white;overflow:auto}
</style>
