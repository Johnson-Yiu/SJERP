import axios from 'axios'

export const api = axios.create({ baseURL: '/api', timeout: 15000 })

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config || {}
    const method = String(config.method || 'get').toLowerCase()
    const status = error.response?.status
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
    const message = data?.detail || (data && typeof data === 'object' ? Object.values(data).flat().join('；') : '') || (retryable ? '后端服务暂时不可用，请稍后重试。' : '请求失败，请稍后重试。')
    return Promise.reject(new Error(message))
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

export async function downloadQuoteExport(id, quoteNo) {
  const response = await api.get(`/quotes/${id}/export/`, { responseType: 'blob', timeout: 120000 })
  const url = URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${quoteNo}.xlsx`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

