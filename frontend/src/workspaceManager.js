import { navigationAccess } from './navigationAccess'
import { advanceSessionEpoch, onWorkspaceWrite, setWorkspaceAccountScope } from './workspaceSession'
import { computed, markRaw, reactive, ref, shallowReactive } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import { installModalNavigationGuard } from './utils/modalNavigation'
import { alertDialog, clearDialogs } from './dialogs'

export const WORKSPACE_LIMIT = 12
export const workspaceQueryKey = '__workspace'
export function businessIdentity(route) {
  const id = route.query.edit || route.query.detail
  return id ? `${route.path}:object:${id}` : route.query.create === '1' ? '' : `${route.path}:list`
}
export function localLocation(route) {
  const query = { ...route.query }; delete query[workspaceQueryKey]
  return { path: route.path, query, hash: route.hash }
}
export function createWorkspaceManager(rootRouter) {
  const tabs = shallowReactive([]), activeId = ref(''), identity = ref('pending'), notice = ref('')
  let closing = false, destroyed = false
  let pendingOpenCount = 0
  let openings = 0, generation = 0, draftSequence = 0
  const pendingObjects = new Map()
  const active = computed(() => tabs.find(t => t.id === activeId.value))
  function rememberScroll() { if (active.value) active.value.scroll = { left: window.scrollX, top: window.scrollY } }
  function url(tab) { const r = tab.router.currentRoute.value; return { path: r.path, query: { ...r.query, [workspaceQueryKey]: tab.id }, hash: r.hash } }
  async function activate(tab, { sync = true } = {}) {
    if (!tabs.includes(tab)) return false
    const switched = activeId.value !== tab.id
    if (switched) rememberScroll()
    activeId.value = tab.id
    if (sync) await rootRouter.push(url(tab))
    if (switched) requestAnimationFrame(() => { if (activeId.value === tab.id) window.scrollTo(tab.scroll || { left: 0, top: 0 }) })
    return true
  }
  async function open(location, options = {}) {
    const key = businessIdentity(rootRouter.resolve(location))
    if (!options.fresh && key && pendingObjects.has(key)) return pendingObjects.get(key)
    pendingOpenCount++
    const promise = openWorkspace(location, options)
    if (!options.fresh && key) pendingObjects.set(key, promise)
    try { return await promise } finally { pendingOpenCount--; if (pendingObjects.get(key) === promise) pendingObjects.delete(key) }
  }
  async function openWorkspace(location, { fresh = false, sync = true } = {}) {
    if (destroyed) return false
    const openedGeneration = generation
    const resolved = rootRouter.resolve(location), clean = localLocation(resolved)
    const access = await navigationAccess(resolved)
    if (openedGeneration !== generation) return false
    if (access !== true) { await rootRouter.replace(access); return false }
    const key = businessIdentity(resolved)
    const existing = !fresh && tabs.find(t => t.key && t.key === key)
    if (existing) { await activate(existing, { sync: false }); if ((Object.keys(clean.query).length || clean.hash) && existing.router.currentRoute.value.fullPath !== existing.router.resolve(clean).fullPath) await existing.router.push(clean); if (sync) await rootRouter.push(url(existing)); return existing }
    if (tabs.length + openings >= WORKSPACE_LIMIT) { notice.value = `已打开 ${WORKSPACE_LIMIT} 个工作区。请先保存并关闭不再使用的标签。`; return false }
    const router = markRaw(createRouter({ history: createMemoryHistory(), routes: rootRouter.options.routes }))
    openings += 1
    const requested = resolved.query[workspaceQueryKey]
    const id = !fresh && typeof requested === 'string' && /^[a-f0-9-]{36}$/i.test(requested) && !tabs.some(t => t.id === requested) ? requested : crypto.randomUUID()
    const tab = reactive({ id, key, draftNumber: resolved.query.create === '1' ? ++draftSequence : null, objectTitle: '', title: resolved.meta.title || '工作区', router, guards: shallowReactive(new Set()), active: computed(() => activeId.value === id), stale: false, revision: 0, busy: 0, scroll: null, closed: false, controller: markRaw(new AbortController()) })
    await router.push(clean); await router.isReady()
    let navigationSequence = 0
    for (const method of ['push', 'replace']) {
      const navigate = router[method].bind(router)
      router[method] = location => {
        const sequence = ++navigationSequence
        tab.navigationMode = method
        return navigate(location).finally(() => { if (sequence === navigationSequence) tab.navigationMode = null })
      }
    }
    // Each pane owns its route guards and route refs. Hidden panes never see another pane's URL.
    router.beforeEach((to, from) => {
      if (tab.closed) return false
      if (tab.retargeting) return true
      const targetKey = businessIdentity(to)
      const opensTask = to.path !== from.path || (targetKey && to.query.detail && targetKey !== businessIdentity(from)) || (to.query.create === '1' && from.query.create !== '1')
      if (opensTask) {
        const location = (to.query.create === '1' || to.query.edit) && to.path !== from.path && !to.query.returnTo ? { path: to.path, query: { ...to.query, returnTo: from.fullPath }, hash: to.hash } : to.fullPath
        void open(location, { fresh: to.query.create === '1' }); return false
      }
      return true
    })
    installModalNavigationGuard(router)
    router.afterEach((to, _from, failure) => {
      if (failure || tab.closed) return
      const nextKey = businessIdentity(to)
      if (nextKey !== tab.key) tab.objectTitle = ''
      tab.key = nextKey
      tab.title = tab.objectTitle || `${to.meta.title || '工作区'}${to.query.create === '1' ? ` · 新建 ${tab.draftNumber}` : to.query.detail || to.query.edit ? ` · #${to.query.detail || to.query.edit}` : ''}`
      if (activeId.value === tab.id) void rootRouter[tab.navigationMode === 'replace' ? 'replace' : 'push'](url(tab))
    })
    tab.title = `${resolved.meta.title || '工作区'}${resolved.query.create === '1' ? ` · 新建 ${tab.draftNumber}` : resolved.query.detail || resolved.query.edit ? ` · #${resolved.query.detail || resolved.query.edit}` : ''}`
    openings -= 1
    if (openedGeneration !== generation) { tab.closed = true; tab.controller.abort(); return false }
    tabs.push(tab); notice.value = ''; await activate(tab, { sync }); return tab
  }
  async function adopt(tab, location) {
    if (!tab || tab.closed) return false
    tab.retargeting = true
    try { return await tab.router.replace(location) } finally { tab.retargeting = false }
  }
  async function confirmExit() {
    for (const tab of tabs) {
      if (tab.busy) return false
      for (const guard of tab.guards) if (!await guard.confirmLeave()) return false
    }
    return true
  }
  async function close(ids) {
    if (closing) return false
    closing = true
    const closingGeneration = generation
    try {
      const targets = tabs.filter(t => ids.includes(t.id))
      // Check the whole batch first. Cancelling leaves every tab and baseline intact.
      for (const tab of targets) {
        if (tab.busy) { await alertDialog({ title: '操作正在提交', message: '请等待当前操作完成后再关闭。' }); return false }
        for (const guard of tab.guards) if (!await guard.confirmLeave()) return false
      }
      if (closingGeneration !== generation || targets.some(tab => !tabs.includes(tab))) return false
      const oldIndex = tabs.indexOf(active.value), wasActive = targets.includes(active.value)
      for (const tab of targets) { tab.closed = true; tab.controller.abort(); tabs.splice(tabs.indexOf(tab), 1) }
      if (wasActive) { if (tabs.length) await activate(tabs[Math.min(oldIndex, tabs.length - 1)]); else { activeId.value = ''; await open('/') } }
      return true
    } finally { closing = false }
  }
  async function reload(tab) {
    if (tab.closed || tab.busy) return false
    for (const guard of tab.guards) if (!await guard.confirmLeave()) return false
    tab.revision++; tab.stale = false; return true
  }
  function move(id, offset) { const i = tabs.findIndex(t => t.id === id), j = i + offset; if (i < 0 || j < 0 || j >= tabs.length) return; const [tab] = tabs.splice(i, 1); tabs.splice(j, 0, tab) }
  function invalidate(source) { for (const tab of tabs) if (tab.id !== source?.id) tab.stale = true }
  function reset(nextIdentity) {
    if (identity.value === nextIdentity) return
    generation++; pendingObjects.clear(); clearDialogs()
    setWorkspaceAccountScope(nextIdentity)
    advanceSessionEpoch()
    identity.value = nextIdentity
    for (const tab of tabs) { tab.closed = true; tab.controller.abort() }
    tabs.splice(0); activeId.value = ''; notice.value = ''
  }
  const removeWrite = onWorkspaceWrite(source => { for (const tab of tabs) if (tab.id !== source) tab.stale = true })
  const remove = rootRouter.afterEach(async (to, _from, failure) => {
    if (failure || destroyed) return
    const tab = tabs.find(t => t.id === to.query[workspaceQueryKey])
    if (tab) {
      await activate(tab, { sync: false })
      const clean = localLocation(to)
      if (tab.router.resolve(clean).fullPath !== tab.router.currentRoute.value.fullPath) {
        const failure = await tab.router.push(clean)
        if (failure) await rootRouter.replace(url(tab))
      }
    } else {
      const opened = await open(to.fullPath, { fresh: to.query.create === '1', sync: false })
      if (opened) await rootRouter.replace(url(opened))
      else if (active.value) await rootRouter.replace(url(active.value))
    }
  })
  return { isOpening: () => pendingOpenCount > 0, tabs, activeId, active, identity, notice, open, activate, adopt, close, confirmExit, reload, move, invalidate, reset, destroy() { destroyed = true; removeWrite(); remove(); reset('destroyed') } }
}
