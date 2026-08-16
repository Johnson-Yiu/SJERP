import axios from 'axios'

export const api = axios.create({ baseURL: '/api', timeout: 15000 })

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    let data = error.response?.data
    if (data instanceof Blob) {
      try { data = JSON.parse(await data.text()) } catch { /* Keep the generic fallback for non-JSON blobs. */ }
    }
    const message = data?.detail || (data && typeof data === 'object' ? Object.values(data).flat().join('；') : '') || '请求失败，请检查后端服务。'
    return Promise.reject(new Error(message))
  },
)

export const listData = (response) => response.data.results || response.data

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

