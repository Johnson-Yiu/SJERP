import { computed, inject, onBeforeUnmount, provide, ref, watch } from 'vue'
import { routerKey } from 'vue-router'
import { workspaceKey } from './useWorkspaceNavigation'
import { confirmDialog } from '../dialogs'

const scopeKey = Symbol('unsaved-editor-scope')
export function provideUnsavedChangesScope() {
  const parent = inject(scopeKey, null)
  const children = new Set()
  const scope = {
    children,
    async confirmLeave() { for (const child of children) if (!await child.confirmLeave()) return false; return true },
    markClean() { for (const child of children) child.markClean() },
    async requestClose(close) {
      if (!await scope.confirmLeave()) return false
      scope.markClean()
      await close()
      return true
    },
  }
  parent?.children.add(scope)
  provide(scopeKey, scope)
  onBeforeUnmount(() => parent?.children.delete(scope))
  return scope
}

// Compare editable values, including nested lines, sets and pending files.
export function unsavedSnapshot(value) {
  return JSON.stringify(value, (_key, item) => {
    if (typeof File !== 'undefined' && item instanceof File) return [item.name, item.size, item.type, item.lastModified]
    if (item instanceof Set) return [...item].sort()
    return item && typeof item === 'object' && !Array.isArray(item) && !(item instanceof Date)
      ? Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item
  })
}

export function useUnsavedChangesGuard({ data, enabled = () => true, busy = () => false, confirmOptions = () => ({}), router: suppliedRouter, routeGuard = true, scope: suppliedScope } = {}) {
  const workspace = inject(workspaceKey, null)
  const router = suppliedRouter || inject(routerKey, null)
  const scope = suppliedScope || inject(scopeKey, null)
  const baseline = ref(null)
  const dirty = computed(() => enabled() && baseline.value !== null && unsavedSnapshot(data()) !== baseline.value)
  const markClean = () => { baseline.value = unsavedSnapshot(data()) }
  let pending
  async function confirmLeave() {
    if (busy()) return false
    if (!dirty.value) return true
    if (!pending) pending = confirmDialog({
      title: '未保存修改', message: '当前修改尚未保存，离开后将丢失。是否继续？',
      cancelText: '继续编辑', confirmText: '放弃修改', danger: true,
      ...confirmOptions(),
    }).finally(() => { pending = null })
    const accepted = await pending
    return accepted && !busy()
  }
  async function requestClose(close) {
    if (!await confirmLeave() || busy()) return false
    markClean()
    await close()
    return true
  }
  const removeRouteGuard = routeGuard ? router?.beforeEach(async (to, from) => {
    if (to.fullPath === from.fullPath) return true
    if (busy()) return false
    if (dirty.value && !await confirmLeave()) return false
    if (scope) {
      for (const child of scope.children) if (child !== scopedGuard && !await child.confirmLeave()) return false
    }
    return !busy()
  }) : undefined
  const removeAfterGuard = router?.afterEach((to, from, failure) => {
    if (!failure && to.fullPath !== from.fullPath && dirty.value) markClean()
  })
  function beforeUnload(event) { if (dirty.value || busy()) { event.preventDefault(); event.returnValue = '' } }
  const stop = watch(() => dirty.value || busy(), value => {
    if (typeof window === 'undefined') return
    window[value ? 'addEventListener' : 'removeEventListener']('beforeunload', beforeUnload)
  }, { flush: 'sync', immediate: true })
  const scopedGuard = { confirmLeave, markClean, dirty }
  workspace?.guards.add(scopedGuard)
  scope?.children.add(scopedGuard)
  onBeforeUnmount(() => { workspace?.guards.delete(scopedGuard); scope?.children.delete(scopedGuard); stop(); removeRouteGuard?.(); removeAfterGuard?.(); if (typeof window !== 'undefined') window.removeEventListener('beforeunload', beforeUnload) })
  return { dirty, markClean, setBaseline: markClean, requestClose }
}
