import { confirmDialog } from '../dialogs'
import { inject } from 'vue'
import { api as sharedApi, listAll as sharedListAll, downloadQuoteExport as sharedQuoteExport, downloadPackingListExport as sharedPackingExport } from '../api'
import { workspaceKey } from './useWorkspaceNavigation'

// Requests belong to a mounted workspace. Closing or changing identity aborts them;
// switching tabs leaves pending work alive and cannot start a second write.
export function useWorkspaceApi() {
  const workspace = inject(workspaceKey, null)
  if (!workspace) return { api: sharedApi, get listAll() { return sharedListAll }, get downloadQuoteExport() { return sharedQuoteExport }, get downloadPackingListExport() { return sharedPackingExport } }
  const request = async config => {
    if (workspace.closed) throw new Error('工作区已关闭，请重新打开。')
    const method = (config.method || 'get').toLowerCase()
    const write = !['get', 'head', 'options'].includes(method)
    const controller = new AbortController()
    const abort = () => controller.abort()
    workspace.controller.signal.addEventListener('abort', abort, { once: true })
    config.signal?.addEventListener('abort', abort, { once: true })
    if (config.signal?.aborted || workspace.controller.signal.aborted) abort()
    if (write) workspace.busy += 1
    try {
      if (write && workspace.stale && !await confirmDialog({ title: '相关数据已更新', message: '其他工作区已保存相关数据。请先核对当前输入；继续提交不会自动合并其他修改。', confirmText: '继续提交', cancelText: '返回核对' })) throw new Error('已保留当前输入，请核对最新数据后再提交。')
      const scoped = { ...config, signal: controller.signal, _workspaceSource: workspace.id }
      delete scoped.url; delete scoped.method; delete scoped.data
      return await (write && method !== 'delete' ? sharedApi[method](config.url, config.data, scoped) : sharedApi[method](config.url, scoped))
    }
    finally { if (write) workspace.busy -= 1; workspace.controller.signal.removeEventListener('abort', abort); config.signal?.removeEventListener('abort', abort) }
  }
  const api = { request,
    get: (url, config) => request({ ...config, url, method: 'get' }),
    delete: (url, config) => request({ ...config, url, method: 'delete' }),
    post: (url, data, config) => request({ ...config, url, data, method: 'post' }),
    put: (url, data, config) => request({ ...config, url, data, method: 'put' }),
    patch: (url, data, config) => request({ ...config, url, data, method: 'patch' }),
  }
  return { api, downloadQuoteExport: (id, number) => sharedQuoteExport(id, number, { signal: workspace.controller.signal }), downloadPackingListExport: (id, number) => sharedPackingExport(id, number, { signal: workspace.controller.signal }), listAll: (url, config = {}) => sharedListAll(url, { ...config, signal: workspace.controller.signal, _workspaceSource: workspace.id }) }
}