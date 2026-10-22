import axios from 'axios'

// 开发环境经 vite proxy 转发到后端 8012；baseURL 统一 /api
const http = axios.create({
  baseURL: '/api',
  timeout: 120000, // LLM + 联网检索可能较慢
})

// —— 对话与场景入口 ——
export const chatApi = (payload) => http.post('/chat', payload)
export const triageApi = (payload) => http.post('/triage', payload)
export const consultationApi = (payload) => http.post('/consultation', payload)
export const medicationApi = (payload) => http.post('/medication', payload)

// —— 健康档案 ——
export const getProfile = (userId) => http.get(`/profile/${userId}`)
export const upsertProfile = (userId, data) => http.put(`/profile/${userId}`, data)

// —— 问诊记录（规格 3.5：近 7/30/180 天）——
export const listRecords = (params) => http.get('/records', { params })
export const listEncounters = (params) => http.get('/encounters', { params })

// —— 预约挂号（规格 3.6）——
export const listDepartments = () => http.get('/departments')
export const getSchedule = (params) => http.get('/appointments/schedule', { params })
export const listAppointments = (params) => http.get('/appointments', { params })
export const createAppointment = (data) => http.post('/appointments', data)
export const cancelAppointment = (id, params) =>
  http.delete(`/appointments/${id}`, { params })

// —— 报告（规格 3.4）——
export const listReports = () => http.get('/reports')
export const interpretReport = (reportId) => http.get(`/reports/${reportId}/interpret`)

// —— 会话与设置（规格 3.7 / 4.2）——
export const listSessions = (params) => http.get('/sessions', { params })
export const listSessionMessages = (sessionId, params) =>
  http.get(`/sessions/${sessionId}/messages`, { params })
export const deleteSession = (sessionId) => http.delete(`/sessions/${sessionId}`)
export const clearAllData = () => http.delete('/sessions')
export const getSettings = () => http.get('/settings')
export const getMetrics = () => http.get('/metrics')

export default http
