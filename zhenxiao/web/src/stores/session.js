import { defineStore } from 'pinia'

export const useSessionStore = defineStore('session', {
  state: () => ({
    userId: localStorage.getItem('zx_user_id') || 'demo_user',
    sessionId: localStorage.getItem('zx_session_id') || '',
  }),
  actions: {
    setSessionId(id) {
      this.sessionId = id
      localStorage.setItem('zx_session_id', id)
    },
    setUserId(id) {
      this.userId = id
      localStorage.setItem('zx_user_id', id)
    },
  },
})
