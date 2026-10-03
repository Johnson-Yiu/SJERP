<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { Bold, Link, List, ListOrdered } from 'lucide-vue-next'
import { alertDialog, inputDialog } from '../dialogs'

const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])
const editor = ref(null)

function sync() {
  emit('update:modelValue', editor.value?.innerHTML || '')
}
function format(command, value = null) {
  editor.value?.focus()
  document.execCommand(command, false, value)
  sync()
}
async function addLink() {
  const url = await inputDialog({ title: '插入链接', message: '请输入以 http、https 或 mailto 开头的链接地址。', label: '链接地址', placeholder: 'https://example.com', required: true, maxLength: 2000, confirmText: '插入链接' })
  if (!url) return
  if (!/^(https?:|mailto:)/i.test(url)) {
    await alertDialog({ title: '链接格式不支持', message: '链接必须以 http、https 或 mailto 开头。' })
    return
  }
  format('createLink', url)
}
onMounted(() => { if (editor.value) editor.value.innerHTML = props.modelValue })
watch(() => props.modelValue, async value => {
  await nextTick()
  if (editor.value && editor.value.innerHTML !== value) editor.value.innerHTML = value || ''
})
</script>

<template>
  <div class="rich-editor">
    <div class="rich-toolbar" aria-label="富文本工具栏">
      <button type="button" title="段落" aria-label="段落" @mousedown.prevent @click="format('formatBlock', 'p')">P</button>
      <button type="button" title="加粗" aria-label="加粗" @mousedown.prevent @click="format('bold')"><Bold :size="15" /></button>
      <button type="button" title="项目列表" aria-label="项目列表" @mousedown.prevent @click="format('insertUnorderedList')"><List :size="15" /></button>
      <button type="button" title="编号列表" aria-label="编号列表" @mousedown.prevent @click="format('insertOrderedList')"><ListOrdered :size="15" /></button>
      <button type="button" title="插入链接" aria-label="插入链接" @mousedown.prevent @click="addLink"><Link :size="15" /></button>
      <span>支持段落、加粗、列表和链接</span>
    </div>
    <div ref="editor" class="rich-editable" contenteditable="true" role="textbox" aria-multiline="true" @input="sync" @blur="sync" />
  </div>
</template>

<style scoped>
.rich-editor{overflow:hidden;border:1px solid #dce3df;border-radius:9px;background:#fff}.rich-editor:focus-within{border-color:#83ad9f;box-shadow:0 0 0 3px #e2efeb}.rich-toolbar{display:flex;align-items:center;gap:4px;padding:6px 8px;border-bottom:1px solid #e5eae7;background:#f7f9f7}.rich-toolbar button{display:grid;width:29px;height:27px;place-items:center;border:0;border-radius:5px;background:transparent;color:#557066}.rich-toolbar button:hover{background:#e2efeb;color:#174f42}.rich-toolbar span{margin-left:auto;color:#83918b;font-size:var(--text-body)}.rich-editable{min-height:136px;padding:11px 12px;outline:none;color:#243a33;font-size:var(--text-body);line-height:1.65;word-break:break-word}.rich-editable :deep(p){margin:0 0 8px}.rich-editable :deep(ul),.rich-editable :deep(ol){margin:0 0 8px;padding-left:22px}.rich-editable:empty:before{content:'记录报价沟通中需要长期保留的重要信息…';color:#9ca8a3;pointer-events:none}@media(max-width:620px){.rich-toolbar span{display:none}}
</style>
