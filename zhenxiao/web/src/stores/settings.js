import { defineStore } from 'pinia'

const THEME_KEY = 'zx_theme'
const LANG_KEY = 'zx_language'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    theme: localStorage.getItem(THEME_KEY) || 'light',
    language: localStorage.getItem(LANG_KEY) || 'zh',
  }),
  getters: {
    isDark() {
      if (this.theme === 'dark') return true
      if (this.theme === 'light') return false
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    },
  },
  actions: {
    setTheme(v) {
      this.theme = v
      localStorage.setItem(THEME_KEY, v)
      this.applyTheme()
    },
    setLanguage(v) {
      this.language = v
      localStorage.setItem(LANG_KEY, v)
      document.documentElement.lang = v === 'zh' ? 'zh-CN' : 'en'
    },
    applyTheme() {
      document.documentElement.classList.toggle('dark', this.isDark)
    },
  },
})
