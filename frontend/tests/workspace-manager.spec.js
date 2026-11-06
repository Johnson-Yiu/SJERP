import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { ref } from 'vue'
vi.mock('../src/workspaceRoutes', () => ({ routes: ['/', '/customers', '/orders', '/purchase-orders'].map(path => ({ path, component: { template: '<div />' }, meta: { title: path } })) }))
vi.mock('../src/dialogs', () => ({ alertDialog: vi.fn().mockResolvedValue(true), clearDialogs: vi.fn() }))
import { createWorkspaceManager, WORKSPACE_LIMIT, newWorkspaceId } from '../src/workspaceManager'
let root, manager
beforeEach(async () => { window.scrollTo = vi.fn(); vi.stubGlobal('requestAnimationFrame', fn => fn()); root = createRouter({ history: createMemoryHistory(), routes: ['/', '/customers', '/orders', '/purchase-orders'].map(path => ({ path, component: {} })) }); await root.push('/'); manager = createWorkspaceManager(root) })
afterEach(() => manager.destroy())
describe('business workspaces', () => {
 it('deduplicates saved objects even during concurrent opening but gives identical drafts separate identities', async () => {
  const [a,b] = await Promise.all([manager.open('/orders?detail=7'), manager.open('/orders?detail=7')]); expect(a.id).toBe(b.id)
  const first = await manager.open('/orders?create=1', { fresh: true }), second = await manager.open('/orders?create=1', { fresh: true })
  expect(first.id).not.toBe(second.id); expect(manager.tabs).toHaveLength(3)
 })
 it('keeps pane route state isolated and switches without invoking dirty guards', async () => {
  const a = await manager.open('/customers?search=Alpha&page=3'), b = await manager.open('/orders?detail=9'); const confirmLeave = vi.fn().mockResolvedValue(false)
  a.guards.add({ confirmLeave, dirty: ref(true) }); await manager.activate(a)
  expect(confirmLeave).not.toHaveBeenCalled(); expect(b.router.currentRoute.value.query.detail).toBe('9'); expect(a.router.currentRoute.value.query.page).toBe('3')
  expect(root.options.history.state.__workspace).toBe(a.id)
 })
 it('batch cancellation is atomic and preserves guards and all tabs', async () => {
  const a = await manager.open('/customers'), b = await manager.open('/orders?create=1', { fresh: true })
  a.guards.add({ confirmLeave: vi.fn().mockResolvedValue(true) }); b.guards.add({ confirmLeave: vi.fn().mockResolvedValue(false) })
  expect(await manager.close([a.id,b.id])).toBe(false); expect(manager.tabs).toHaveLength(2); expect(a.closed).toBe(false)
 })
 it('blocks closing writes, aborts requests only after accepted close and enforces a hard limit', async () => {
  const a = await manager.open('/customers'); a.busy=1; expect(await manager.close([a.id])).toBe(false); a.busy=0
  for (let i=1;i<WORKSPACE_LIMIT;i++) await manager.open('/orders?create=1', { fresh: true })
  expect(await manager.open('/orders?create=1', { fresh: true })).toBe(false); expect(manager.tabs).toHaveLength(WORKSPACE_LIMIT)
  expect(await manager.close([a.id])).toBe(true); expect(a.controller.signal.aborted).toBe(true); expect(manager.notice.value).toBe('')
 })
 it('identity reset destroys old panes and reload cancellation retains dirty state', async () => {
  const a=await manager.open('/orders?edit=4'); a.stale=true; a.guards.add({confirmLeave:vi.fn().mockResolvedValue(false)})
  expect(await manager.reload(a)).toBe(false); expect(a.stale).toBe(true); expect(a.revision).toBe(0)
  manager.reset('next-account'); expect(manager.tabs).toHaveLength(0); expect(a.controller.signal.aborted).toBe(true)
 })
})

it('an identity change during a close confirmation cannot splice the next account tabs', async () => {
 const old=await manager.open('/customers');let resolve
 old.guards.add({confirmLeave:()=>new Promise(done=>{resolve=done})})
 const closing=manager.close([old.id]);await Promise.resolve()
 manager.reset('new-account');const fresh=await manager.open('/orders')
 resolve(true);expect(await closing).toBe(false);expect(manager.tabs.map(t=>t.id)).toEqual([fresh.id])
})
it('a successful draft save adopts the same pane and order movement preserves identities', async () => {
 const draft=await manager.open('/orders?create=1',{fresh:true}), list=await manager.open('/customers')
 await manager.adopt(draft,'/orders?detail=42');expect(manager.tabs).toHaveLength(2);expect(draft.key).toBe('/orders:object:42')
 manager.move(draft.id,1);expect(manager.tabs.map(t=>t.id)).toEqual([list.id,draft.id])
})

it('URL synchronization does not overwrite a switched workspace scroll position', async () => {
 const a=await manager.open('/customers'),b=await manager.open('/orders')
 a.scroll={left:0,top:500}; b.scroll={left:0,top:0}
 await manager.activate(a)
 Object.defineProperty(window,'scrollY',{value:500,configurable:true})
 await manager.activate(b);expect(b.scroll.top).toBe(0)
 expect(window.scrollTo).toHaveBeenLastCalledWith({left:0,top:0})
})

it('page-local replace keeps browser history replacement semantics', async () => {
 const order=await manager.open('/orders?detail=9')
 await order.router.replace('/orders?detail=9&tab=items')
 await manager.open('/customers')
 root.back(); await vi.waitFor(()=>expect(root.currentRoute.value.query.tab).toBe('items'))
 root.back(); await vi.waitFor(()=>expect(root.currentRoute.value.path).toBe('/'))
})

it('identical draft URLs keep distinct native history identities through Back and Forward', async () => {
 const first=await manager.open('/orders?create=1',{fresh:true}), second=await manager.open('/orders?create=1',{fresh:true})
 expect(root.currentRoute.value.fullPath).toBe('/orders?create=1')
 expect(root.options.history.state.__workspace).toBe(second.id)
 root.back();await vi.waitFor(()=>expect(manager.activeId.value).toBe(first.id))
 root.forward();await vi.waitFor(()=>expect(manager.activeId.value).toBe(second.id))
 expect(root.currentRoute.value.fullPath).toBe('/orders?create=1')
})

it('workspace identity remains available on development HTTP origins without randomUUID', () => {
 const original = globalThis.crypto
 vi.stubGlobal('crypto', { getRandomValues: original.getRandomValues.bind(original) })
 try { const first = newWorkspaceId(), second = newWorkspaceId(); expect(first).toMatch(/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/); expect(first).not.toBe(second) }
 finally { vi.stubGlobal('crypto', original) }
})
