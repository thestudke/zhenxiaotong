<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useSettingsStore } from './stores/settings'
import { t } from './i18n'

const route = useRoute()
const router = useRouter()
const settings = useSettingsStore()

const navItems = [
  { path: '/triage', key: 'nav.triage' },
  { path: '/chat', key: 'nav.chat' },
  { path: '/medication', key: 'nav.medication' },
  { path: '/encounters', key: 'nav.encounters' },
  { path: '/reports', key: 'nav.reports' },
  { path: '/appointments', key: 'nav.appointments' },
  { path: '/settings', key: 'nav.settings' },
]

function label(key) {
  return t(settings.language, key)
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo-area">
        <div class="logo-icon">诊</div>
        <h1>诊小通Agent</h1>
        <p>{{ label('app.subtitle') }}</p>
      </div>

      <ul class="nav-menu">
        <li
          v-for="item in navItems"
          :key="item.path"
          :class="{ active: route.path === item.path }"
          @click="router.push(item.path)"
        >
          <span class="bar"></span>
          <span class="label">{{ label(item.key) }}</span>
        </li>
      </ul>
    </aside>

    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100%;
}

/* —— 左侧侧边栏 —— */
.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #0f766e;
  color: #fff;
  display: flex;
  flex-direction: column;
}

.logo-area {
  padding: 24px 20px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

.logo-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #fff;
  color: #0f766e;
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.logo-area h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 1px;
}

.logo-area p {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.72);
}

.nav-menu {
  list-style: none;
  margin: 0;
  padding: 12px 0;
  flex: 1;
}

.nav-menu li {
  position: relative;
  display: flex;
  align-items: center;
  height: 46px;
  padding: 0 20px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.82);
  font-size: 14px;
  transition: background 0.2s;
}

.nav-menu li:hover {
  background: rgba(255, 255, 255, 0.08);
}

.nav-menu li.active {
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  font-weight: 600;
}

.nav-menu .bar {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 22px;
  border-radius: 0 3px 3px 0;
  background: transparent;
}

.nav-menu li.active .bar {
  background: #34d399;
}

.nav-menu .label {
  margin-left: 4px;
}

/* —— 右侧主内容 —— */
.main-content {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-page);
  padding: 20px;
}
</style>
