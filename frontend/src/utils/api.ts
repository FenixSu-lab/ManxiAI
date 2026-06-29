/*
 * Shared Axios client for backend API calls.
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import Cookies from 'js-cookie'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const getApiErrorMessage = (error: any, fallback: string) => {
  const data = error.response?.data
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  if (data.message) return data.message
  if (data.error) return data.error

  const fields = [
    'name',
    'url',
    'file',
    'type',
    'qa_pairs',
    'question',
    'answer',
    'base_url',
    'api_key',
    'model',
    'provider_type',
    'hit_handling_method',
    'directly_return_similarity',
    'non_field_errors'
  ]

  for (const field of fields) {
    const value = data[field]
    if (Array.isArray(value) && value.length > 0) {
      const first = value[0]
      if (typeof first === 'string') return first
      if (typeof first === 'object') return JSON.stringify(first)
    }
    if (typeof value === 'string') return value
  }

  return fallback
}

api.interceptors.request.use(
  (config) => {
    const token = Cookies.get('token')
    if (token) {
      config.headers.Authorization = `Token ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const { response } = error

    if (response) {
      switch (response.status) {
        case 401:
          ElMessage.error('Your session has expired. Please log in again.')
          Cookies.remove('token')
          window.location.href = '/login'
          break
        case 403:
          ElMessage.error('You do not have permission to access this resource.')
          break
        case 404:
          ElMessage.error('The requested resource was not found.')
          break
        case 500:
          ElMessage.error('The server encountered an internal error.')
          break
        default:
          // Let page-level form handlers display field-specific validation errors.
          if (response.status >= 500) {
            ElMessage.error(response.data?.message || 'Request failed.')
          }
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('Backend request timed out. Check PostgreSQL connection latency.')
    } else {
      ElMessage.error('Network error. Check your backend service and connection.')
    }

    return Promise.reject(error)
  }
)

export default api
