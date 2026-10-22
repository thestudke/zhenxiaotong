import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import App from './App.vue'
import router from './router'
import './style.css'
import { useSettingsStore } from './stores/settings'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(ElementPlus)

// 应用初始主题
useSettingsStore(pinia).applyTheme()
// 跟随系统时，监听系统主题变化
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  const settings = useSettingsStore(pinia)
  if (settings.theme === 'system') settings.applyTheme()
})

app.mount('#app')
