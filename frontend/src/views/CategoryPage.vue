<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api } = useWorkspaceApi()
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { Check, ChevronRight, FolderPlus, GripVertical, Layers3, Pencil, Plus, Settings2, Tags, Trash2, X } from 'lucide-vue-next'
import { listData } from '../api'
import { confirmDialog } from '../dialogs'
import PageLoadState from '../components/PageLoadState.vue'
import { apiErrorMessage as baseApiErrorMessage } from '../utils/apiErrors.js'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'
import { useAccessControl } from '../accessControl'

const categories = ref([])
const { can } = useAccessControl()
const loading = ref(true), hasLoaded = ref(false), loadError = ref(''), saveError = ref('')
const selectedId = ref(null)
const search = ref('')
const categoryModal = ref(false)
const saving = ref(false)
const draggingId = ref(null)
const childDropTargetId = ref(null)
const nodeDropTarget = reactive({ id: null, after: false })
const draggingAttributeId = ref(null)
const expandedCategoryIds = ref(new Set())
const treeExpansionInitialized = ref(false)
const message = reactive({ text: '', error: false })
const operationError = ref('')
const categoryForm = reactive({ id: null, name: '', parent: '', description: '' })
const addingAttribute = ref(false)
const attributeSaving = ref(false)
const newAttribute = reactive({ name: '', include_in_sku: false, include_in_sales_model: false, uppercase: false, required: false })
const editingAttribute = ref(null)
const editAttributeName = ref('')
const reorderReview = ref(null), reorderSaving = ref(false), reorderError = ref('')
function apiErrorMessage(error) {
  const data = error?.response?.data || error?.data
  return data?.affected_products?.length && data.detail
    ? `${data.detail} 受影响产品：${data.affected_products.map(row => `${row.code} · ${row.name}`).join('；')}`
    : baseApiErrorMessage(error)
}

const guard = useUnsavedChangesGuard({ data: () => categoryForm, enabled: () => categoryModal.value, busy: () => saving.value || attributeSaving.value || reorderSaving.value })
const attributeGuard = useUnsavedChangesGuard({ data: () => ({ attribute: addingAttribute.value ? newAttribute : null, name: editingAttribute.value ? editAttributeName.value : null }), enabled: () => addingAttribute.value || Boolean(editingAttribute.value), busy: () => attributeSaving.value || reorderSaving.value })
async function selectCategory(id) { if (id === selectedId.value) return; if (!await attributeGuard.requestClose(() => { addingAttribute.value = false; editingAttribute.value = null })) return; selectedId.value = id }
function cancelNewAttribute() { return attributeGuard.requestClose(() => { addingAttribute.value = false }) }
function closeCategory() { return guard.requestClose(() => { categoryModal.value = false }) }
function expandAll(expand) { expandedCategoryIds.value = expand ? new Set(categories.value.filter(row => row.child_count).map(row => row.id)) : new Set() }
const byId = computed(() => new Map(categories.value.map(row => [row.id, { ...row, children: [] }])))
const roots = computed(() => {
  const map = byId.value
  for (const node of map.values()) if (node.parent && map.has(node.parent)) map.get(node.parent).children.push(node)
  const result = [...map.values()].filter(node => !node.parent || !map.has(node.parent))
  const sort = nodes => { nodes.sort((a, b) => a.sort_order - b.sort_order || a.id - b.id); nodes.forEach(node => sort(node.children)) }
  sort(result)
  return result
})
const flatTree = computed(() => {
  const rows = []
  const keyword = search.value.trim().toLowerCase()
  const walk = (nodes, depth = 0, parent = null) => nodes.forEach((node, index) => {
    rows.push({ node, depth, parent, index })
    if (keyword || expandedCategoryIds.value.has(node.id)) walk(node.children, depth + 1, node.id)
  })
  walk(roots.value)
  return keyword ? rows.filter(row => row.node.name.toLowerCase().includes(keyword)) : rows
})
const selected = computed(() => categories.value.find(row => row.id === selectedId.value) || null)
const selectedPath = computed(() => {
  if (!selected.value) return ''
  const parts = []; let node = selected.value
  while (node) { parts.unshift(node.name); node = categories.value.find(row => row.id === node.parent) }
  return parts.join(' / ')
})
const maxDepth = computed(() => { const depth = node => node.parent ? 1 + depth(categories.value.find(row => row.id === node.parent) || { parent: null }) : 1; return categories.value.reduce((max, node) => Math.max(max, depth(node)), 0) })
const attributeCount = computed(() => categories.value.reduce((sum, row) => sum + row.attributes.length, 0))
const categoryOptions = computed(() => {
  const excluded = new Set()
  if (categoryForm.id) {
    const addChildren = parentId => categories.value.filter(item => item.parent === parentId).forEach(item => { excluded.add(item.id); addChildren(item.id) })
    excluded.add(categoryForm.id); addChildren(categoryForm.id)
  }
  const rows = []
  const walk = (nodes, depth = 0, path = []) => nodes.forEach(node => {
    if (!excluded.has(node.id)) rows.push({ id: node.id, label: `${'　'.repeat(depth)}${depth ? '└ ' : ''}${[...path, node.name].join(' / ')}` })
    walk(node.children, depth + 1, [...path, node.name])
  })
  walk(roots.value)
  return rows
})

function notify(text, error = false) { operationError.value = error ? text : ''; Object.assign(message, { text, error }); setTimeout(() => { message.text = '' }, 2600) }
function restoreViewport(position) {
  if (!position || (!position.top && !position.left)) return
  let attempts = 0
  const restore = () => {
    window.scrollTo(position.left, position.top)
    attempts += 1
    const maximumTop = Math.max(0, document.documentElement.scrollHeight - window.innerHeight)
    if (attempts < 12 && maximumTop < position.top) window.setTimeout(restore, 80)
  }
  window.requestAnimationFrame(restore)
}
async function load(preserve = selectedId.value, viewport = { left: window.scrollX, top: window.scrollY }) {
  loading.value = true
  loadError.value = ''
  try {
    categories.value = listData(await api.get('/categories/tree/'))
    hasLoaded.value = true
    const expandableIds = new Set(categories.value.filter(row => row.child_count).map(row => row.id))
    if (!treeExpansionInitialized.value) {
      expandedCategoryIds.value = expandableIds
      treeExpansionInitialized.value = true
    } else {
      expandedCategoryIds.value = new Set([...expandedCategoryIds.value].filter(id => expandableIds.has(id)))
    }
    selectedId.value = categories.value.some(row => row.id === preserve) ? preserve : categories.value[0]?.id || null
  } catch (e) { loadError.value = apiErrorMessage(e) } finally {
    loading.value = false
    await nextTick()
    restoreViewport(viewport)
  }
}
function openCategory(node = null, parent = '') {
  if (!can('categories', node?.id ? 'update' : 'create')) return
  Object.assign(categoryForm, { id: node?.id || null, name: node?.name || '', parent: node?.parent ?? parent ?? '', description: node?.description || '' })
  saveError.value = ''; message.text = ''
  categoryModal.value = true
  guard.markClean()
}
async function saveCategory() {
  if (saving.value) return
  saveError.value = ''; message.text = ''
  if (!can('categories', categoryForm.id ? 'update' : 'create')) return
  saving.value = true
  try {
    const payload = { name: categoryForm.name, parent: categoryForm.parent ? Number(categoryForm.parent) : null, description: categoryForm.description }
    const response = categoryForm.id ? await api.patch(`/categories/${categoryForm.id}/`, payload) : await api.post('/categories/', payload)
    guard.markClean(); categoryModal.value = false; await load(response.data.id); notify('分类已保存')
  } catch (e) { saveError.value = apiErrorMessage(e); notify(saveError.value, true) } finally { saving.value = false }
}
async function removeCategory(node) {
  if (!can('categories', 'delete')) return
  if (!await confirmDialog({ title: '确认删除分类', message: `确定删除分类“${node.name}”吗？有子分类或关联产品时不能删除。`, confirmText: '确认删除', danger: true })) return
  try { await api.delete(`/categories/${node.id}/`); await load(); notify('分类已删除') } catch (e) { notify(apiErrorMessage(e), true) }
}
async function startAttribute() { if (!can('categories', 'create') || !await attributeGuard.requestClose(() => { editingAttribute.value = null })) return; Object.assign(newAttribute, { name: '', include_in_sku: false, include_in_sales_model: false, uppercase: false, required: false }); addingAttribute.value = true; attributeGuard.markClean() }
const requiredRuleMessage = '“必填”属性必须用于中文 SKU 名称或 Sales Model。'
const canRequire = attribute => Boolean(attribute.include_in_sku || attribute.include_in_sales_model)
const attributeKey = attribute => String(attribute?.key || attribute?.name || '').trim().toLocaleLowerCase()
function categoryLineage(category) {
  const lineage = []
  const visited = new Set()
  let current = category
  while (current && !visited.has(current.id)) {
    visited.add(current.id)
    lineage.unshift(current)
    current = categories.value.find(item => Number(item.id) === Number(current.parent))
  }
  return lineage
}
function rebuildEffectiveAttributes(category) {
  const merged = new Map()
  categoryLineage(category).forEach(source => {
    ;(source.attributes || []).forEach(attribute => {
      merged.set(attributeKey(attribute), { ...attribute, inherited: source.id !== category.id, source_category: source.name })
    })
  })
  category.effective_attributes = [...merged.values()]
  category.sku_name_preview = category.effective_attributes
    .filter(attribute => attribute.include_in_sku)
    .map(attribute => {
      const value = attribute.default_value || `[${attribute.name}]`
      return attribute.uppercase && attribute.default_value ? value.toUpperCase() : value
    })
    .join('-')
}
function applyCreatedAttribute(attribute) {
  const category = categories.value.find(item => Number(item.id) === Number(attribute.category))
  if (!category) return
  category.attributes = [...(category.attributes || []), attribute]
  // Rebuild from the local hierarchy instead of re-fetching the entire page.
  // This keeps the viewport stable and updates inherited rows immediately.
  categories.value.forEach(rebuildEffectiveAttributes)
}
function toggleNewRequired(event) {
  if (newAttribute.required && !canRequire(newAttribute)) {
    newAttribute.required = false
    if (event?.target) event.target.checked = false
    notify(requiredRuleMessage, true)
  }
}
async function saveNewAttribute() {
  if (attributeSaving.value) return
  if (!can('categories', 'create')) return
  if (!newAttribute.name.trim()) return notify('请输入属性名称。', true)
  if (newAttribute.required && !canRequire(newAttribute)) return notify(requiredRuleMessage, true)
  attributeSaving.value = true
  try {
    const response = await api.post('/category-attributes/', { category: selectedId.value, name: newAttribute.name.trim(), key: newAttribute.name.trim(), include_in_sku: newAttribute.include_in_sku, include_in_sales_model: newAttribute.include_in_sales_model, uppercase: newAttribute.uppercase, required: newAttribute.required, sort_order: selected.value.attributes.length })
    applyCreatedAttribute(response.data)
    attributeGuard.markClean()
    addingAttribute.value = false
    notify('属性已新增')
  } catch (e) { notify(apiErrorMessage(e), true) } finally { attributeSaving.value = false }
}
async function startEditAttribute(attribute) {
  if (!can('categories', 'update')) return
  if (attribute.inherited) return notify('这项属性来自上级分类，请到该分类修改。', true)
  if (!await attributeGuard.requestClose(() => { addingAttribute.value = false; editingAttribute.value = null })) return
  editingAttribute.value = attribute; editAttributeName.value = attribute.name; attributeGuard.markClean()
}
async function saveAttributeName(attribute) {
  if (attributeSaving.value) return
  if (!can('categories', 'update')) return
  if (!editAttributeName.value.trim()) return notify('属性名称不能为空。', true)
  attributeSaving.value = true
  try {
    const payload = { category: selectedId.value, name: editAttributeName.value.trim(), key: attribute.key, default_value: attribute.default_value, unit: attribute.unit, include_in_sku: attribute.include_in_sku, include_in_sales_model: attribute.include_in_sales_model, uppercase: attribute.uppercase, required: attribute.required, sort_order: attribute.sort_order }
    attribute.inherited ? await api.post('/category-attributes/', payload) : await api.patch(`/category-attributes/${attribute.id}/`, { name: payload.name })
    editingAttribute.value = null; await load(selectedId.value); notify(attribute.inherited ? '已在当前分类创建属性覆盖' : '属性名称已更新')
  } catch (e) { notify(apiErrorMessage(e), true) } finally { attributeSaving.value = false }
}
async function toggleRule(attribute, field, event = null) {
  if (!can('categories', 'update')) return
  if (attribute.inherited) return notify('这项属性来自上级分类，请到该分类修改规则。', true)
  const previous = attribute[field]
  const next = !previous
  const remainsGenerative = field === 'include_in_sku'
    ? next || attribute.include_in_sales_model
    : field === 'include_in_sales_model'
      ? attribute.include_in_sku || next
      : canRequire(attribute)
  if ((field === 'required' && next && !canRequire(attribute)) || (attribute.required && ['include_in_sku', 'include_in_sales_model'].includes(field) && !remainsGenerative)) {
    if (event?.target) event.target.checked = previous
    notify(requiredRuleMessage, true)
    return
  }
  attribute[field] = next
  try {
    const response = await api.patch(`/category-attributes/${attribute.id}/`, { [field]: next })
    const persisted = typeof response.data[field] === 'boolean' ? response.data[field] : next
    categories.value.forEach(category => {
      ;[...(category.attributes || []), ...(category.effective_attributes || [])]
        .filter(item => item.id === attribute.id)
        .forEach(item => { item[field] = persisted })
    })
    attribute[field] = persisted
  } catch (e) {
    attribute[field] = previous
    notify(apiErrorMessage(e), true)
  }
}
async function removeAttribute(attribute) {
  if (!can('categories', 'delete')) return
  if (!await confirmDialog({ title: '确认删除属性', message: `确定删除属性“${attribute.name}”吗？未冻结 SKU 引用的身份属性不能删除，系统会检查并拒绝不允许的操作。`, confirmText: '确认删除', danger: true })) return
  try { await api.delete(`/category-attributes/${attribute.id}/`); await load(selectedId.value); notify('属性已删除') } catch (e) { notify(apiErrorMessage(e), true) }
}
function startAttributeDrag(attribute, event) {
  if (attribute.inherited) return
  draggingAttributeId.value = attribute.id
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(attribute.id))
}
async function dropAttribute(target) {
  if (!can('categories', 'update')) return
  const sourceId = draggingAttributeId.value
  draggingAttributeId.value = null
  if (!sourceId || target.inherited || sourceId === target.id) return
  const ordered = [...selected.value.effective_attributes.filter(attribute => !attribute.inherited)]
  const sourceIndex = ordered.findIndex(attribute => attribute.id === sourceId)
  const targetIndex = ordered.findIndex(attribute => attribute.id === target.id)
  if (sourceIndex < 0 || targetIndex < 0) return
  const [moved] = ordered.splice(sourceIndex, 1)
  ordered.splice(targetIndex, 0, moved)
  try {
    const response = await api.post('/category-attributes/reorder/', { category: selectedId.value, ids: ordered.map(attribute => attribute.id), preview: true })
    reorderReview.value = { category: selectedId.value, ids: ordered.map(attribute => attribute.id), changes: response.data.changes || [] }
    reorderError.value = ''
  } catch (e) { notify(apiErrorMessage(e), true) }
}
async function confirmAttributeReorder() {
  if (!can('categories', 'update') || !reorderReview.value || reorderSaving.value) return
  reorderSaving.value = true; reorderError.value = ''
  try {
    await api.post('/category-attributes/reorder/', { category: reorderReview.value.category, ids: reorderReview.value.ids, confirm: true })
    reorderReview.value = null
    await load(selectedId.value)
    notify('属性顺序已更新；SKU 名称和 Sales Model 已更新。')
  } catch (e) { reorderError.value = apiErrorMessage(e) } finally { reorderSaving.value = false }
}
function cancelAttributeReorder() { if (reorderSaving.value) return; reorderReview.value = null; reorderError.value = '' }
function reorderDiff(oldValue, newValue) {
  const oldText = String(oldValue || ''), newText = String(newValue || '')
  if (oldText === newText) return { old: [{ text: oldText || '—', changed: false }], next: [{ text: newText || '—', changed: false }] }
  let prefix = 0
  while (prefix < oldText.length && prefix < newText.length && oldText[prefix] === newText[prefix]) prefix += 1
  let suffix = 0
  while (suffix < oldText.length - prefix && suffix < newText.length - prefix && oldText[oldText.length - suffix - 1] === newText[newText.length - suffix - 1]) suffix += 1
  return {
    old: [{ text: oldText.slice(0, prefix), changed: false }, { text: oldText.slice(prefix, oldText.length - suffix) || '∅', changed: true }, { text: oldText.slice(oldText.length - suffix), changed: false }].filter(item => item.text),
    next: [{ text: newText.slice(0, prefix), changed: false }, { text: newText.slice(prefix, newText.length - suffix) || '∅', changed: true }, { text: newText.slice(newText.length - suffix), changed: false }].filter(item => item.text),
  }
}
function dragStart(id, event) {
  if (!can('categories', 'update')) { event.preventDefault(); return }
  draggingId.value = id
  childDropTargetId.value = null
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(id))
}
function dragEnd() {
  draggingId.value = null
  childDropTargetId.value = null
  nodeDropTarget.id = null
  nodeDropTarget.after = false
}
function dragOverChild(id) {
  if (!draggingId.value || draggingId.value === id) return
  childDropTargetId.value = id
  nodeDropTarget.id = null
}
function dragOverNode(id, event) {
  if (!draggingId.value || draggingId.value === id) return
  childDropTargetId.value = null
  nodeDropTarget.id = id
  nodeDropTarget.after = event.clientY >= event.currentTarget.getBoundingClientRect().top + event.currentTarget.getBoundingClientRect().height / 2
}
function clearNodeDropTarget() {
  nodeDropTarget.id = null
  nodeDropTarget.after = false
}
function dropOnNode(row, event) {
  if (!can('categories', 'update')) return dragEnd()
  if (!draggingId.value || draggingId.value === row.node.id) return dragEnd()
  const rect = event.currentTarget.getBoundingClientRect()
  let index = row.index + (event.clientY >= rect.top + rect.height / 2 ? 1 : 0)
  const source = categories.value.find(item => item.id === draggingId.value)
  const sameParent = source && (source.parent || null) === (row.parent || null)
  if (sameParent) {
    const sourceIndex = categories.value
      .filter(item => (item.parent || null) === (row.parent || null))
      .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
      .findIndex(item => item.id === draggingId.value)
    if (sourceIndex >= 0 && sourceIndex < index) index -= 1
  }
  moveDragged(row.parent, index)
}
async function moveDragged(parent, index) {
  if (!can('categories', 'update') || !draggingId.value) return
  try { await api.post('/categories/reorder/', { id: draggingId.value, parent, index }); await load(draggingId.value); notify('分类位置已更新') }
  catch (e) { notify(apiErrorMessage(e), true) } finally { dragEnd() }
}
function directAttribute(attribute) { return !attribute.inherited }
function toggleCategoryExpansion(id) {
  const next = new Set(expandedCategoryIds.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expandedCategoryIds.value = next
}
onMounted(load)
</script>

<template>
  <div>
    <div class="page-head"><div><h2>产品分类</h2><p>按分类整理产品，并设置属性和 SKU 命名规则。</p></div><button v-if="can('categories', 'create')" class="btn btn-primary" @click="openCategory()"><FolderPlus :size="16" /> 新建根分类</button></div>
    <div class="category-summary">
      <div><Layers3 :size="18" /><span>分类总数<strong>{{ categories.length }}</strong></span></div>
      <div><Tags :size="18" /><span>根分类<strong>{{ roots.length }}</strong></span></div>
      <div><ChevronRight :size="18" /><span>最大层级<strong>{{ maxDepth }}</strong></span></div>
      <div><Settings2 :size="18" /><span>自定义属性<strong>{{ attributeCount }}</strong></span></div>
    </div>

    <p v-if="operationError" class="sku-save-error" role="alert">{{ operationError }}</p><div class="category-layout">
      <section class="panel tree-panel">
        <div class="panel-heading"><div><h3>分类列表</h3><p>拖动分类可调整顺序；放到右侧“放入”区域可设为子分类。</p></div><button v-if="can('categories', 'create')" class="icon-action" title="新建根分类" @click="openCategory()"><Plus :size="16" /></button></div>
        <input v-model="search" class="tree-search" placeholder="搜索分类名称" aria-label="搜索分类" />
        <div class="tree-tools"><button type="button" @click="expandAll(true)">全部展开</button><button type="button" @click="expandAll(false)">全部收起</button><button type="button" :disabled="loading" @click="load()">刷新</button></div><PageLoadState :loading="loading" :has-loaded="hasLoaded" :error="loadError" @retry="load()" />
        <div v-if="!loading && !loadError && !flatTree.length" class="tree-empty">{{ search ? '没有找到分类，请换个名称试试。' : '还没有分类。请先新建根分类。' }}</div>
        <div v-if="flatTree.length" class="tree-list">
          <template v-for="row in flatTree" :key="row.node.id">
            <div class="drop-line" :style="{ marginLeft: `${row.depth * 22 + 10}px` }" @dragover.prevent="clearNodeDropTarget" @drop.stop="moveDragged(row.parent, row.index)" />
            <div class="tree-node" :class="{ active: selectedId === row.node.id, dragging: draggingId === row.node.id, 'drop-before': nodeDropTarget.id === row.node.id && !nodeDropTarget.after, 'drop-after': nodeDropTarget.id === row.node.id && nodeDropTarget.after }" :style="{ paddingLeft: `${row.depth * 22 + 8}px` }"  :draggable="can('categories', 'update')" @dragstart="dragStart(row.node.id, $event)" @dragend="dragEnd" @dragover.prevent="dragOverNode(row.node.id, $event)" @drop.stop="dropOnNode(row, $event)" @click="selectCategory(row.node.id)">
              <span class="drag-handle" title="拖拽排序"><GripVertical :size="15" /></span><button v-if="row.node.children.length" type="button" class="branch-toggle" :title="expandedCategoryIds.has(row.node.id) ? '收起子分类' : '展开子分类'" @click.stop="toggleCategoryExpansion(row.node.id)">{{ expandedCategoryIds.has(row.node.id) ? '▾' : '▸' }}</button><span v-else class="branch-mark">·</span>
              <div class="node-copy"><strong :title="row.node.name">{{ row.node.name }}</strong><small v-if="search">{{ categories.find(item => item.id === row.node.parent)?.name || '根分类' }}</small></div>
              <span v-if="draggingId && draggingId !== row.node.id" class="node-child-drop" :class="{ active: childDropTargetId === row.node.id }" title="放入此分类成为子分类" @dragover.prevent.stop="dragOverChild(row.node.id)" @drop.stop="moveDragged(row.node.id, row.node.children.length)">放入</span><span v-if="row.node.children.length" class="child-count">{{ row.node.children.length }}</span>
            </div>
          </template>
          <div class="root-drop" @dragover.prevent="clearNodeDropTarget" @drop="moveDragged(null, roots.length)">拖到这里移动为根分类</div>
        </div>
      </section>

      <section class="panel config-panel">
        <div v-if="!selected" class="config-empty"><Layers3 :size="34" /><strong>尚未选择分类</strong><p>请从左侧列表选择分类，查看或编辑属性。</p></div>
        <template v-else>
          <div class="category-hero">
            <div><small>{{ selectedPath }}</small><h3>{{ selected.name }}</h3><p>{{ selected.description || '暂无分类说明' }}</p></div>
            <div class="hero-actions"><button v-if="can('categories', 'create')" class="btn btn-secondary" @click="openCategory(null, selected.id)"><Plus :size="14" /> 子分类</button><button v-if="can('categories', 'update')" class="icon-action" title="编辑分类" @click="openCategory(selected)"><Pencil :size="15" /></button><button v-if="can('categories', 'delete')" class="icon-action danger" title="删除分类" @click="removeCategory(selected)"><Trash2 :size="15" /></button></div>
          </div>
          <div class="sku-preview"><div><small>中文 SKU 名称预览</small><strong>{{ selected.sku_name_preview || '选择用于中文 SKU 名称的属性后，这里会显示预览' }}</strong></div><p>按分类属性顺序预览，不会更改 SKU Code。</p></div>
          <div class="attribute-heading"><div><h4>分类属性</h4><p>选择用于中文 SKU 名称或 Sales Model 的属性，也可拖动调整顺序。</p><p>分类属性用于产品的 SKU 参数方案。已发布的方案不会随模板自动变化；如需更新，请到产品页分析后发布。</p></div><button v-if="can('categories', 'create')" class="btn btn-secondary" :disabled="addingAttribute || attributeSaving" @click="startAttribute"><Plus :size="14" /> 新增属性</button></div>
          <div v-if="!selected.effective_attributes.length && !addingAttribute" class="attribute-empty">此分类及其上级分类还没有属性。</div>
          <div v-else class="attribute-table-wrap"><table class="attribute-table"><thead><tr><th>属性名称</th><th>来源</th><th>生成中文SKU</th><th>生成销售型号</th><th>自动大写</th><th>必填</th><th></th></tr></thead><tbody>
            <tr v-for="attribute in selected.effective_attributes" :key="attribute.key" :class="{ 'attribute-dragging': draggingAttributeId === attribute.id, inherited: attribute.inherited }" @dragover.prevent @drop.prevent="dropAttribute(attribute)"><td><div class="attribute-title"><span v-if="!attribute.inherited" class="attribute-drag-handle" draggable="true" title="拖拽排序" @dragstart.stop="startAttributeDrag(attribute, $event)" @dragend="draggingAttributeId = null"><GripVertical :size="15" /></span><span v-else class="attribute-inherited-mark">↳</span><template v-if="editingAttribute?.key === attribute.key"><div class="attribute-name-editor"><input v-model.trim="editAttributeName" :disabled="attributeSaving" class="attribute-name-input" @keyup.enter="saveAttributeName(attribute)" /><button class="inline-save" :disabled="attributeSaving" title="保存名称" @click.stop="saveAttributeName(attribute)"><Check :size="14" /></button></div></template><strong v-else>{{ attribute.name }}</strong></div></td><td><span :class="['source-badge', { inherited: attribute.inherited }]">{{ attribute.inherited ? `继承：${attribute.source_category}` : '当前分类' }}</span></td><td><label class="rule-switch" :class="{ locked: attribute.inherited }"><input type="checkbox" :checked="attribute.include_in_sku" :disabled="attribute.inherited || !can('categories', 'update')" @change.stop="toggleRule(attribute, 'include_in_sku', $event)" /><span /></label></td><td><label class="rule-switch" :class="{ locked: attribute.inherited }"><input type="checkbox" :checked="attribute.include_in_sales_model" :disabled="attribute.inherited || !can('categories', 'update')" @change.stop="toggleRule(attribute, 'include_in_sales_model', $event)" /><span /></label></td><td><label class="rule-switch" :class="{ locked: attribute.inherited }"><input type="checkbox" :checked="attribute.uppercase" :disabled="attribute.inherited || !can('categories', 'update')" @change.stop="toggleRule(attribute, 'uppercase', $event)" /><span /></label></td><td><label class="rule-switch" :class="{ locked: attribute.inherited }"><input type="checkbox" :checked="attribute.required" :disabled="attribute.inherited || !can('categories', 'update')" @change.stop="toggleRule(attribute, 'required', $event)" /><span /></label></td><td><div class="row-actions"><button v-if="!attribute.inherited && can('categories', 'update')" class="icon-action" title="修改属性名称" @click.stop="startEditAttribute(attribute)"><Pencil :size="14" /></button><span v-else class="read-only-note">只读</span><button v-if="directAttribute(attribute) && can('categories', 'delete')" type="button" class="icon-action danger" title="删除属性" @pointerdown.stop @click.stop.prevent="removeAttribute(attribute)"><Trash2 :size="14" /></button></div></td></tr>
            <tr v-if="addingAttribute && can('categories', 'create')" class="new-attribute-row"><td><input v-model.trim="newAttribute.name" class="attribute-name-input" :disabled="attributeSaving" autofocus placeholder="输入属性名称，例如：色温" @keyup.enter="saveNewAttribute" /></td><td><span class="source-badge">当前分类</span></td><td><label class="rule-switch"><input v-model="newAttribute.include_in_sku" :disabled="attributeSaving" type="checkbox" /><span /></label></td><td><label class="rule-switch"><input v-model="newAttribute.include_in_sales_model" :disabled="attributeSaving" type="checkbox" /><span /></label></td><td><label class="rule-switch"><input v-model="newAttribute.uppercase" :disabled="attributeSaving" type="checkbox" /><span /></label></td><td><label class="rule-switch"><input v-model="newAttribute.required" :disabled="attributeSaving" type="checkbox" @change="toggleNewRequired" /><span /></label></td><td><div class="row-actions"><button class="inline-save" :disabled="attributeSaving" title="保存属性" @click="saveNewAttribute"><Check :size="14" /></button><button class="icon-action" :disabled="attributeSaving" title="取消" @click="cancelNewAttribute"><X :size="14" /></button></div></td></tr>
          </tbody></table></div>
        </template>
      </section>
    </div>

    <div v-if="categoryModal && (categoryForm.id ? can('categories', 'update') : can('categories', 'create'))" class="modal-backdrop" @mousedown.self="closeCategory"><form class="modal" role="dialog" aria-modal="true" :aria-label="categoryForm.id ? '编辑分类' : '新建分类'" @submit.prevent="saveCategory"><div class="modal-head"><h3>{{ categoryForm.id ? '编辑分类' : '新建分类' }}</h3><button type="button" class="mini-btn" :disabled="saving" @click="closeCategory"><X :size="17" /></button></div><div class="modal-body"><p v-if="saveError" class="sku-save-error" role="alert">{{ saveError }}</p><div class="form-grid" :inert="saving"><div class="field"><label>分类名称 *</label><input v-model.trim="categoryForm.name" aria-label="分类名称" maxlength="100" required /></div><div class="field"><label>上级分类</label><select v-model="categoryForm.parent" aria-label="上级分类"><option value="">无（根分类）</option><option v-for="item in categoryOptions" :key="item.id" :value="item.id">{{ item.label }}</option></select></div><div class="field full"><label>分类说明</label><textarea v-model="categoryForm.description" /></div></div></div><div class="modal-foot"><button type="button" class="btn btn-secondary" :disabled="saving" @click="closeCategory">取消</button><button v-if="categoryForm.id ? can('categories', 'update') : can('categories', 'create')" class="btn btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存分类' }}</button></div></form></div>

    <div v-if="reorderReview && can('categories', 'update')" class="modal-backdrop reorder-review-backdrop"><section class="modal reorder-review-modal"><div class="modal-head"><div><h3>确认参数顺序调整</h3><p>确认后会更新当前 SKU 的中文名称和 Sales Model，并保存旧值。历史报价、订单、采购和库存单据不变。</p></div><button type="button" class="mini-btn" @click="cancelAttributeReorder"><X :size="17" /></button></div><div class="modal-body"><p v-if="!reorderReview.changes.length" class="muted">本次调整不会改变现有 SKU 名称或 Sales Model。</p><div v-else class="reorder-review-list"><div v-for="change in reorderReview.changes" :key="change.sku_id" class="reorder-review-row"><strong>{{ change.sku_code }}</strong><div class="reorder-review-fields"><div><small>内部名称</small><p><span v-for="(part,index) in reorderDiff(change.old_display_name_cn, change.new_display_name_cn).old" :key="`old-name-${change.sku_id}-${index}`" :class="{ 'diff-removed': part.changed }">{{ part.text }}</span></p><p class="next-value"><span v-for="(part,index) in reorderDiff(change.old_display_name_cn, change.new_display_name_cn).next" :key="`new-name-${change.sku_id}-${index}`" :class="{ 'diff-added': part.changed }">{{ part.text }}</span></p></div><div><small>Sales Model</small><p><span v-for="(part,index) in reorderDiff(change.old_sales_model, change.new_sales_model).old" :key="`old-model-${change.sku_id}-${index}`" :class="{ 'diff-removed': part.changed }">{{ part.text }}</span></p><p class="next-value"><span v-for="(part,index) in reorderDiff(change.old_sales_model, change.new_sales_model).next" :key="`new-model-${change.sku_id}-${index}`" :class="{ 'diff-added': part.changed }">{{ part.text }}</span></p></div></div></div></div><p v-if="reorderError" class="sku-save-error" role="alert">{{ reorderError }}</p><p class="identity-review-hint">保存前会检查名称、Sales Model 和历史名称是否与其他 SKU 重复；如有重复，将不会保存。</p></div><div class="modal-foot"><button type="button" class="btn btn-secondary" @click="cancelAttributeReorder">取消</button><button v-if="can('categories', 'update')" type="button" class="btn btn-primary" :disabled="reorderSaving" @click="confirmAttributeReorder">{{ reorderSaving ? '检查并保存中…' : '确认并更新 SKU' }}</button></div></section></div>

    <div v-if="message.text" class="toast" :class="{ error: message.error }">{{ message.text }}</div>
  </div>
</template>

<style scoped>
.category-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}.category-summary>div{display:flex;align-items:center;gap:11px;padding:13px 15px;background:white;border:1px solid var(--line);border-radius:11px;color:#477064}.category-summary span,.category-summary strong{display:block}.category-summary span{font-size:var(--text-caption);color:#82918b}.category-summary strong{font-size:var(--text-section);color:#24483e;margin-top:3px}.category-layout{display:grid;grid-template-columns:360px minmax(0,1fr);gap:14px}.tree-panel,.config-panel{min-height:570px}.panel-heading,.category-hero,.attribute-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.panel-heading{padding:17px;border-bottom:1px solid var(--line)}.panel-heading h3,.attribute-heading h4{margin:0;font-size:var(--text-section)}.panel-heading p,.attribute-heading p{margin:4px 0 0;color:#86938e;font-size:var(--text-caption)}.icon-action{width:31px;height:31px;border:1px solid #dce4df;border-radius:7px;background:white;color:#60726b;display:inline-grid;place-items:center}.icon-action:hover{color:#1f6857;border-color:#9ebeb4}.icon-action.danger{color:#a75b5b}.tree-search{width:calc(100% - 28px);margin:13px 14px 7px;border:1px solid #dfe6e2;border-radius:8px;padding:9px 10px;outline:0}.tree-list{padding:4px 9px 16px}.drop-line{height:7px;border-radius:5px}.drop-line:hover{background:#b8d9ce}.tree-node{min-height:51px;display:flex;align-items:center;gap:7px;border:1px solid transparent;border-radius:9px;padding-right:8px;cursor:pointer}.tree-node:hover{background:#f3f7f5}.tree-node.active{background:#e8f2ee;border-color:#c2dbd2}.tree-node.dragging{opacity:.4}.drag-handle{color:#a1aca8;cursor:grab;flex:none}.branch-mark{width:12px;color:#5d7e73}.node-copy{flex:1;min-width:0}.node-copy strong,.node-copy small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.node-copy strong{font-size:var(--text-body);color:#32483f}.node-copy small{font-size:var(--text-caption);color:#8a9691;margin-top:3px}.child-count{font-size:var(--text-caption);background:#dbe9e4;color:#43695e;border-radius:12px;padding:2px 6px}.root-drop{margin:10px;padding:9px;border:1px dashed #c7d6d0;border-radius:8px;text-align:center;font-size:var(--text-caption);color:#89958f}.root-drop:hover{background:#edf6f2;border-color:#7fa99c}.tree-empty,.config-empty,.attribute-empty{padding:50px 20px;text-align:center;color:#8a9792;font-size:var(--text-caption)}.config-empty{min-height:500px;display:flex;flex-direction:column;justify-content:center;align-items:center}.config-empty strong{font-size:var(--text-body);color:#546861;margin-top:10px}.config-empty p{margin:4px}.category-hero{padding:20px;border-bottom:1px solid var(--line)}.category-hero small{color:#83918c;font-size:var(--text-caption)}.category-hero h3{margin:5px 0 3px;font-size:var(--text-section)}.category-hero p{margin:0;color:#75847e;font-size:var(--text-caption)}.hero-actions,.row-actions{display:flex;gap:7px;align-items:center}.hero-actions .btn{padding:8px 11px}.sku-preview{margin:16px 18px;padding:13px 15px;border-radius:10px;background:#163f37;color:white;display:flex;align-items:center;justify-content:space-between;gap:20px}.sku-preview small,.sku-preview strong{display:block}.sku-preview small{font-size:var(--text-caption);color:#9ac0b4}.sku-preview strong{font-size:var(--text-body);margin-top:5px}.sku-preview p{margin:0;max-width:280px;color:#a8c9bf;font-size:var(--text-caption)}.attribute-heading{padding:4px 18px 12px}.attribute-heading .btn{padding:8px 11px}.attribute-table-wrap{overflow:auto;border-top:1px solid var(--line)}.attribute-table{width:100%;min-width:720px;border-collapse:collapse}.attribute-table th{padding:10px 12px;text-align:left;background:#f7f9f7;color:#7f8d88;font-size:var(--text-body)}.attribute-table td{padding:12px;border-top:1px solid #edf0ee;color:#4b5d56;font-size:var(--text-body)}.attribute-table td strong,.attribute-table td small{display:block}.attribute-table td strong{color:#2f443d;font-size:var(--text-body)}.attribute-table td small{color:#8b9692;font-size:var(--text-caption);margin-top:3px}.source-badge{display:inline-block;padding:4px 7px;border-radius:12px;background:#e5f1ec;color:#306954;font-size:var(--text-secondary)}.source-badge.inherited{background:#f0edf7;color:#685987}.rule-switch input{position:absolute;opacity:0}.rule-switch span{display:block;width:32px;height:18px;border-radius:20px;background:#ced8d4;position:relative;transition:.2s}.rule-switch span:after{content:'';position:absolute;width:14px;height:14px;border-radius:50%;background:white;top:2px;left:2px;transition:.2s;box-shadow:0 1px 3px #0002}.rule-switch input:checked+span{background:#26705c}.rule-switch input:checked+span:after{transform:translateX(14px)}.rule-options>label:not(:first-child){display:flex;align-items:center;gap:7px;margin:8px 0;font-weight:400}.rule-options input{width:auto!important}.modal .full{grid-column:1/-1}@media(max-width:1000px){.category-layout{grid-template-columns:1fr}.tree-panel{min-height:350px}.category-summary{grid-template-columns:repeat(2,1fr)}}
.tree-node{min-height:36px}.drop-line{height:4px}.tree-list{padding-top:2px}.tree-search{padding:7px 10px}.category-summary span{font-size:var(--text-body)}.category-summary strong{font-size:var(--text-dialog)}.panel-heading h3,.attribute-heading h4{font-size:var(--text-section)}.panel-heading p,.attribute-heading p{font-size:var(--text-body)}.node-copy strong{font-size:var(--text-body)}.child-count,.root-drop{font-size:var(--text-caption)}.category-hero small{font-size:var(--text-caption)}.category-hero h3{font-size:var(--text-section)}.category-hero p{font-size:var(--text-body)}.sku-preview small{font-size:var(--text-caption)}.sku-preview strong{font-size:var(--text-section)}.sku-preview p{font-size:var(--text-body)}.tree-empty,.config-empty,.attribute-empty{font-size:var(--text-body)}.config-empty strong{font-size:var(--text-section)}.attribute-table th{font-size:var(--text-body)}.attribute-table td{font-size:var(--text-body)}.attribute-table td strong{font-size:var(--text-body)}.source-badge{font-size:var(--text-secondary)}.tree-node{min-height:36px}.attribute-name-editor{display:flex;align-items:center;gap:7px}.attribute-name-input{width:100%;min-width:140px;border:1px solid #c6d9d2;border-radius:7px;padding:7px 9px;font:inherit;color:#2f443d;outline:0}.attribute-name-input:focus{border-color:#36806b;box-shadow:0 0 0 3px #36806b18}.inline-save{width:30px;height:30px;display:inline-grid;place-items:center;flex:none;border:0;border-radius:7px;background:#226b57;color:#fff}.new-attribute-row td{background:#f3f8f5}.new-attribute-row .attribute-name-input{background:#fff}.attribute-table-wrap{overflow-x:hidden}.attribute-table{min-width:0;table-layout:fixed}.attribute-table th:nth-child(1),.attribute-table td:nth-child(1){width:31%}.attribute-table th:nth-child(2),.attribute-table td:nth-child(2){width:19%}.attribute-table th:nth-child(3),.attribute-table td:nth-child(3),.attribute-table th:nth-child(4),.attribute-table td:nth-child(4),.attribute-table th:nth-child(5),.attribute-table td:nth-child(5){width:12%}.attribute-table th:nth-child(6),.attribute-table td:nth-child(6){width:14%}.attribute-table td{padding:10px 8px}.row-actions{justify-content:flex-end;gap:5px}.row-actions .icon-action{width:29px;height:29px;flex:none}.rule-switch{display:inline-block;position:relative;z-index:1}.rule-switch.locked{opacity:.45;cursor:not-allowed}.rule-switch.locked span{cursor:not-allowed}.read-only-note{color:#8f7ca9;font-size:var(--text-caption);white-space:nowrap}.attribute-table tr.inherited{background:#fcfbfe}.attribute-title{display:flex;align-items:center;gap:6px;min-width:0}.attribute-drag-handle{width:22px;height:24px;display:inline-grid;place-items:center;flex:none;color:#91a19a;cursor:grab;border-radius:5px}.attribute-drag-handle:hover{background:#e7f1ed;color:#2b705c}.attribute-drag-handle:active{cursor:grabbing}.attribute-dragging{opacity:.45}.attribute-inherited-mark{width:15px;flex:none;color:#8e7fa6}.branch-toggle{width:18px;height:24px;padding:0;border:0;background:transparent;color:#5d7e73;cursor:pointer;line-height:1;border-radius:5px}.branch-toggle:hover{background:#e4f0eb;color:#1f6956}.branch-mark{display:inline-grid;place-items:center;height:24px}
.drag-handle{display:inline-grid;place-items:center;width:22px;height:24px;border-radius:5px;color:#a1aca8;cursor:grab;flex:none}.drag-handle:hover{background:#e7f1ed;color:#2b705c}.drag-handle:active{cursor:grabbing}.tree-node.drop-before,.tree-node.drop-after{background:#edf7f3;border-color:#b5d8ca}.tree-node.drop-before{box-shadow:inset 0 3px 0 #2b705c}.tree-node.drop-after{box-shadow:inset 0 -3px 0 #2b705c}.node-child-drop{display:inline-flex;align-items:center;justify-content:center;min-width:36px;padding:4px 6px;border:1px dashed #a9c5ba;border-radius:6px;background:#f3f9f6;color:#4d7b6c;font-size:var(--text-caption);line-height:1;white-space:nowrap}.node-child-drop.active,.node-child-drop:hover{border-color:#26705c;background:#dcefe7;color:#1f6654}
.attribute-table th:nth-child(1),.attribute-table td:nth-child(1){width:28%}.attribute-table th:nth-child(2),.attribute-table td:nth-child(2){width:18%}.attribute-table th:nth-child(3),.attribute-table td:nth-child(3),.attribute-table th:nth-child(4),.attribute-table td:nth-child(4),.attribute-table th:nth-child(5),.attribute-table td:nth-child(5),.attribute-table th:nth-child(6),.attribute-table td:nth-child(6){width:10%}.attribute-table th:nth-child(7),.attribute-table td:nth-child(7){width:14%}.attribute-title:has(.attribute-name-editor) .attribute-drag-handle{display:none}.attribute-name-editor{display:grid;grid-template-columns:minmax(0,1fr) 30px;flex:1;min-width:0;width:100%;gap:5px}.attribute-name-editor .attribute-name-input{width:100%;min-width:0}.source-badge{white-space:nowrap}
.reorder-review-backdrop{z-index:140}.reorder-review-modal{width:min(980px,calc(100vw - 28px));max-height:calc(100vh - 48px)}.reorder-review-list{display:grid;gap:10px;max-height:52vh;overflow:auto}.reorder-review-row{padding:12px;border:1px solid #dbe7e1;border-radius:9px;background:#fbfdfc}.reorder-review-row>strong{display:block;margin-bottom:8px;color:#285d4e}.reorder-review-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.reorder-review-fields>div{padding:10px;border-radius:7px;background:#fff;border:1px solid #e6eeea}.reorder-review-fields small{display:block;color:#7a8b83;font-size:var(--text-caption);margin-bottom:4px}.reorder-review-fields p{margin:4px 0;color:#29483e;font-size:var(--text-body);line-height:1.6;word-break:break-word}.reorder-review-fields p.next-value{border-top:1px dashed #dce8e2;padding-top:6px}.diff-removed{background:#ffd9d5;color:#a52f24;text-decoration:line-through;border-radius:3px;padding:1px 2px}.diff-added{background:#ccefdc;color:#176443;border-radius:3px;padding:1px 2px}.identity-review-hint{margin:12px 0 0;color:#687c73;font-size:var(--text-caption);line-height:1.7}.sku-save-error{margin:12px 0 0;padding:10px;border-radius:7px;background:#fff2f0;color:#b42318;font-size:var(--text-body)}@media(max-width:650px){.reorder-review-fields{grid-template-columns:1fr}}
.tree-tools{display:flex;flex-wrap:wrap;gap:12px;padding:4px 14px 12px}.tree-tools button{border:0;background:transparent;color:#286950;cursor:pointer}.category-hero>div,.attribute-heading>div{min-width:0}.category-hero h3,.category-hero p,.category-hero small{overflow-wrap:anywhere}.hero-actions{flex-wrap:wrap;flex-shrink:0}.category-layout{grid-template-columns:minmax(260px,320px) minmax(0,1fr)}.tree-panel,.config-panel{min-width:0}.category-hero,.attribute-heading{flex-wrap:wrap}.attribute-heading p{line-height:1.6}.tree-list{overflow-x:auto}.tree-node{min-width:240px}@media(max-width:1100px){.category-layout{grid-template-columns:1fr}.tree-panel{min-height:0;max-height:440px;overflow:auto}}
</style>
