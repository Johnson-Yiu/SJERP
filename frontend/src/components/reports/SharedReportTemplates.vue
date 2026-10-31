<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  templates: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  canCreate: { type: Boolean, default: false },
  canManage: { type: Boolean, default: false },
  canDelete: { type: Boolean, default: false },
  currentId: { type: [String, Number], default: '' },
  currentReady: { type: Boolean, default: false },
  editor: { type: Object, default: null },
  history: { type: Object, default: null },
})
const emit = defineEmits(['refresh', 'use', 'begin-create', 'edit', 'save', 'close-editor', 'publish', 'unpublish', 'delete', 'history', 'close-history'])
const pending = ref(null)
const draft = ref({ name: '', description: '' })
watch(() => props.editor, value => {
  draft.value = value ? { name: value.name || '', description: value.description || '' } : { name: '', description: '' }
}, { immediate: true, deep: true })
function request(action, template) {
  if (action === 'delete' || action === 'unpublish') pending.value = { action, template }
  else emit(action, template)
}
function confirmPending() {
  if (!pending.value) return
  emit(pending.value.action, pending.value.template)
  pending.value = null
}
function cancelPending() { pending.value = null }
function submit() {
  if (!draft.value.name.trim()) return
  emit('save', { name: draft.value.name.trim(), description: draft.value.description.trim() })
}
function actionLabel(action) { return action === 'delete' ? '删除' : '取消发布' }
function timeLabel(value) { return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—' }
</script>

<template>
  <section class="shared-templates" aria-label="团队共享模板">
    <header class="shared-header">
      <div><h2>团队共享模板</h2><p>模板只保存报表条件；每次使用仍按当前账号的数据权限重新查询。</p></div>
      <div class="shared-header-actions"><button type="button" @click="emit('refresh')">刷新</button><button v-if="canCreate" type="button" class="primary" :disabled="!currentReady" @click="emit('begin-create')">根据当前查询创建</button></div>
    </header>
    <p v-if="error" class="shared-error" role="alert">{{ error }} <button type="button" @click="emit('refresh')">重试</button></p>
    <p v-else-if="loading" class="shared-empty" role="status">正在加载团队模板…</p>
    <p v-else-if="!templates.length" class="shared-empty">当前没有可用的已发布模板。</p>
    <div v-else class="template-list">
      <article v-for="template in templates" :key="template.id" class="template-card" :class="{ active: String(currentId) === String(template.id) }">
        <div class="template-card-main"><div class="template-title"><strong>{{ template.name }}</strong><span :class="template.published ? 'published' : 'draft'">{{ template.published ? '已发布' : '草稿' }}</span><span v-if="String(currentId) === String(template.id)" class="using">当前使用</span></div><p v-if="template.description">{{ template.description }}</p><small>更新于 {{ timeLabel(template.updated_at) }} · {{ template.creator_name }}</small></div>
        <div class="template-actions"><button type="button" :disabled="!template.can_use" @click="emit('use', template)">{{ String(currentId) === String(template.id) ? '重新载入' : '使用模板' }}</button><button v-if="canManage" type="button" :disabled="!template.can_use" @click="emit('edit', template)">编辑</button><button v-if="canManage" type="button" @click="request(template.published ? 'unpublish' : 'publish', template)">{{ template.published ? '取消发布' : '发布' }}</button><button v-if="canDelete" type="button" @click="request('delete', template)">删除</button><button v-if="canManage" type="button" @click="emit('history', template)">操作记录</button></div>
        <p v-if="template.can_use === false" class="template-unavailable">当前账号没有该模板来源或筛选维度的查看权限。</p>
        <div v-if="pending && pending.template.id === template.id" class="template-confirm" role="alert"><span>确认{{ actionLabel(pending.action) }}“{{ template.name }}”？</span><button type="button" class="danger" @click="confirmPending">确认</button><button type="button" @click="cancelPending">返回</button></div>
      </article>
    </div>
    <form v-if="editor" class="template-editor" @submit.prevent="submit">
      <div><h3>{{ editor.mode === 'edit' ? '编辑团队模板' : '创建团队模板' }}</h3><p>保存的是当前查询配置，不包含查询结果或固定金额。</p></div>
      <label>模板名称<input v-model="draft.name" maxlength="80" required></label>
      <label>模板说明（可选）<input v-model="draft.description" maxlength="300"></label>
      <div class="template-editor-actions"><button type="submit" class="primary">保存{{ editor.mode === 'edit' ? '修改' : '草稿' }}</button><button type="button" @click="emit('close-editor')">取消</button></div>
    </form>
    <section v-if="history" class="template-history" aria-label="团队模板操作记录">
      <header><h3>{{ history.template?.name }} · 操作记录</h3><button type="button" @click="emit('close-history')">关闭</button></header>
      <p v-if="!history.rows?.length" class="shared-empty">暂无操作记录。</p>
      <table v-else><thead><tr><th>时间</th><th>操作</th><th>操作人</th><th>版本</th></tr></thead><tbody><tr v-for="row in history.rows" :key="row.id"><td>{{ timeLabel(row.created_at) }}</td><td>{{ row.action_display }}</td><td>{{ row.operator_name || '—' }}</td><td>{{ row.metadata?.config_version || '—' }}</td></tr></tbody></table>
    </section>
  </section>
</template>

<style scoped>
.shared-templates{background:#fff;border:1px solid #dfe7e2;border-radius:14px;padding:22px;min-width:0}.shared-header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}.shared-header h2{font-size:var(--text-section);margin:0 0 7px;color:#294838}.shared-header p,.template-card p,.template-card small,.template-editor p{margin:0;color:#6b7c70;font-size:var(--text-caption);line-height:1.7}.shared-header-actions,.template-actions,.template-editor-actions{display:flex;gap:8px;flex-wrap:wrap}.shared-templates button{border:1px solid #d5dfd6;border-radius:7px;padding:8px 11px;background:#fff;color:#365d47;cursor:pointer;font-size:var(--text-caption)}.shared-templates button:disabled{opacity:.45;cursor:default}.shared-templates button.primary{background:#286c52;color:#fff;border-color:#286c52}.shared-templates button.danger{color:#a34232;border-color:#e2beb6}.shared-empty{padding:24px;text-align:center;color:#718377;font-size:var(--text-caption)}.shared-error{color:#a54335;background:#fff8f5;border:1px solid #edcbc5;border-radius:8px;padding:12px;line-height:1.7}.template-list{display:grid;gap:10px;margin-top:16px}.template-card{border:1px solid #e1e9e2;border-radius:10px;padding:14px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px}.template-card.active{border-color:#6aab8c;background:#f7fbf8}.template-title{display:flex;align-items:center;gap:8px;flex-wrap:wrap;color:#294838}.template-title strong{font-size:var(--text-body);overflow-wrap:anywhere}.template-title span{font-size:11px;border-radius:99px;padding:2px 7px}.published{background:#e5f4ea;color:#27704d}.draft{background:#fff1dc;color:#8a642c}.using{background:#eaf0ff;color:#405b94}.template-card-main>p{margin-top:5px}.template-actions{justify-content:flex-end;align-content:start}.template-unavailable{grid-column:1/-1;color:#a06a36!important;background:#fff8ed;border-radius:6px;padding:6px 8px}.template-confirm{grid-column:1/-1;display:flex;gap:8px;align-items:center;flex-wrap:wrap;border-top:1px solid #e9eeea;padding-top:10px;color:#81592d;font-size:var(--text-caption)}.template-editor{display:grid;grid-template-columns:minmax(180px,1fr) minmax(180px,1fr) auto;gap:12px;align-items:end;margin-top:16px;padding-top:16px;border-top:1px solid #e8eee9}.template-editor h3,.template-history h3{font-size:var(--text-body);margin:0 0 5px;color:#294838}.template-editor label{display:flex;flex-direction:column;gap:6px;color:#5d7164;font-size:var(--text-caption)}.template-editor input{box-sizing:border-box;width:100%;height:40px;border:1px solid #d5dfd6;border-radius:7px;padding:0 10px;color:#314a3c;font:inherit}.template-history{margin-top:18px;border-top:1px solid #e8eee9;padding-top:14px}.template-history header{display:flex;justify-content:space-between;align-items:center}.template-history table{width:100%;border-collapse:collapse;font-size:var(--text-caption);margin-top:8px}.template-history th,.template-history td{text-align:left;padding:9px;border-bottom:1px solid #edf1ed}@media(max-width:700px){.shared-templates{padding:16px}.template-card{grid-template-columns:1fr}.template-actions{justify-content:flex-start}.template-editor{grid-template-columns:1fr}.template-editor-actions{grid-column:1}}
</style>
