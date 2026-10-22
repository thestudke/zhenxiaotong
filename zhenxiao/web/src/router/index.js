import { createRouter, createWebHistory } from 'vue-router'
import TriageView from '../views/TriageView.vue'
import ChatView from '../views/ChatView.vue'
import EncounterView from '../views/EncounterView.vue'
import ReportView from '../views/ReportView.vue'
import AppointmentView from '../views/AppointmentView.vue'
import SettingsView from '../views/SettingsView.vue'

const routes = [
  { path: '/', redirect: '/triage' },
  { path: '/triage', component: TriageView, meta: { title: '智能分诊台' } },
  { path: '/chat', component: ChatView, meta: { title: '线上问诊' } },
  { path: '/medication', component: ChatView, meta: { title: '用药咨询' } },
  { path: '/encounters', component: EncounterView, meta: { title: '问诊记录' } },
  { path: '/reports', component: ReportView, meta: { title: '报告查询' } },
  { path: '/appointments', component: AppointmentView, meta: { title: '预约挂号' } },
  { path: '/settings', component: SettingsView, meta: { title: '系统设置' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
