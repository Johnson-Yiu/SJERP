import axios from 'axios'

export const api = axios.create({ baseURL: '/api', timeout: 15000 })

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const data = error.response?.data
    const message = data?.detail || (data && typeof data === 'object' ? Object.values(data).flat().join('；') : '') || '请求失败，请检查后端服务。'
    return Promise.reject(new Error(message))
  },
)

export const listData = (response) => response.data.results || response.data

