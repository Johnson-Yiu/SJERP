import { sessionEpoch, notifyWorkspaceWrite, notifySessionBoundary } from './workspaceSession.js'
import axios from 'axios'
import { apiErrorMessage } from './utils/apiErrors.js'
export { apiErrorMessage, formatApiError } from './utils/apiErrors.js'

export const api = axios.create({ baseURL: '/api', timeout: 15000, xsrfCookieName: 'csrftoken', xsrfHeaderName: 'X-CSRFToken' })

api.interceptors.request.use(config => { config._sessionEpoch ??= sessionEpoch(); return config })

api.interceptors.response.use(
  (response) => {
    if (response.config._sessionEpoch !== sessionEpoch()) return Promise.reject(new Error('账号已变化，请重新载入。'))
    if (!['get', 'head', 'options'].includes((response.config.method || 'get').toLowerCase())) notifyWorkspaceWrite(response.config._workspaceSource)
    return response
  },
  async (error) => {
    const config = error.config || {}
    if (config._sessionEpoch !== undefined && config._sessionEpoch !== sessionEpoch()) return Promise.reject(error)
    const method = String(config.method || 'get').toLowerCase()
    const status = error.response?.status
    if (status === 401) notifySessionBoundary()
    const retryable = !status || [500, 502, 503, 504].includes(status)
    const canRetry = ['get', 'head', 'options'].includes(method) && retryable && !config.signal?.aborted
    const retries = config._backendRetryCount || 0
    if (canRetry && retries < 5) {
      config._backendRetryCount = retries + 1
      // Django briefly stops accepting requests while its development reloader
      // applies backend changes.  Keep read-only requests alive through that window.
      await new Promise(resolve => setTimeout(resolve, [250, 500, 1000, 2000, 3000][retries]))
      return api.request(config)
    }
    let data = error.response?.data
    if (data instanceof Blob) {
      try { data = JSON.parse(await data.text()) } catch { /* Keep the generic fallback for non-JSON blobs. */ }
    }
    const normalized = new Error(apiErrorMessage({ isApiError: true, status, data, code: error.code }))
    Object.assign(normalized, { status: status || null, data, rawData: error.response?.data, response: error.response, code: error.code, isApiError: true })
    return Promise.reject(normalized)
  },
)

export const listData = (response) => response.data.results || response.data

// Aggregated inventory and finance screens must include every API page.
export async function listAll(url, config = {}) {
  const rows = []
  let page = 1
  while (true) {
    const response = await api.get(url, { ...config, params: { ...config.params, page } })
    rows.push(...listData(response))
    if (!response.data.next) return rows
    page += 1
  }
}

export async function downloadQuoteExport(id, quoteNo, config = {}) {
  const response = await api.get(`/quotes/${id}/export/`, { ...config, responseType: 'blob', timeout: 120000 })
  const url = URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${quoteNo}.xlsx`
  document.body.appendChild(anchor)
  anchor.click()
  setTimeout(() => {
    anchor.remove()
    URL.revokeObjectURL(url)
  }, 1000)
}

export async function downloadPackingListExport(id, shipmentNo, config = {}) {
  const response = await api.get(`/shipments/${id}/export-packing-list/`, { ...config, responseType: 'blob', timeout: 120000 })
  const url = URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `PackingList-${shipmentNo || id}.xlsx`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

