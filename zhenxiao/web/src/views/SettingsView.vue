<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSettingsStore } from '../stores/settings'
import { t } from '../i18n'
import { getSettings, getMetrics, clearAllData } from '../api'
import HealthProfile from './ProfileView.vue'

const settings = useSettingsStore()

const status = ref(null)
const metrics = ref(null)
const loading = ref(false)
const clearing = ref(false)

const themes = [
  { value: 'light', key: 'theme.light' },
  { value: 'dark', key: 'theme.dark' },
  { value: 'system', key: 'theme.system' },
]

const languages = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
]

function tl(key) {
  return t(settings.language, key)
}

async function loadStatus() {
  loading.value = true
  try {
    const [s, m] = await Promise.all([getSettings(), getMetrics()])
    status.value = s.data
    metrics.value = m.data
  } catch (e) {
    ElMessage.error('状态加载失败：' + (e?.response?.data?.detail || e?.message || ''))
  } finally {
    loading.value = false
  }
}

async function onClearAll() {
  try {
    await ElMessageBox.confirm(
      '将删除全部会话、消息、问诊记录与预约数据，且不可恢复。确认继续？',
      '一键清空全部数据',
      { type: 'warning', confirmButtonText: '确认清空', confirmButtonClass: 'el-button--danger' }
    )
  } catch {
    return
  }
  clearing.value = true
  try {
    const { data } = await clearAllData()
    const d = data.deleted || {}
    ElMessage.success(
      `已清空：会话 ${d.sessions ?? 0}、消息 ${d.messages ?? 0}、记录 ${d.encounters ?? 0}、预约 ${d.appointments ?? 0}`
    )
    await loadStatus()
  } catch (e) {
    ElMessage.error('清空失败：' + (e?.response?.data?.detail || e?.message || ''))
  } finally {
    clearing.value = false
  }
}

onMounted(loadStatus)
</script>

<template>
  <el-card>
    <el-tabs>
      <el-tab-pane :label="tl('settings.general')">
        <div class="setting-section">
          <div class="setting-label">{{ tl('settings.theme') }}</div>
          <el-radio-group
            :model-value="settings.theme"
            @update:model-value="settings.setTheme"
          >
            <el-radio-button v-for="th in themes" :key="th.value" :value="th.value">
              {{ tl(th.key) }}
            </el-radio-button>
          </el-radio-group>
        </div>

        <div class="setting-section">
          <div class="setting-label">{{ tl('settings.language') }}</div>
          <el-radio-group
            :model-value="settings.language"
            @update:model-value="settings.setLanguage"
          >
            <el-radio-button v-for="l in languages" :key="l.value" :value="l.value">
              {{ l.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
      </el-tab-pane>

      <!-- 规格书 3.7 / M7：模型、API 地址、联网检索状态 + 一键清空全部数据 -->
      <el-tab-pane :label="tl('settings.system')">
        <div v-loading="loading" class="status-area">
          <div class="status-grid">
            <div class="status-card">
              <div class="status-label">大模型状态</div>
              <div class="status-value">
                <el-tag :type="status?.llm_enabled ? 'success' : 'info'">
                  {{ status?.llm_enabled ? '已启用' : '降级模式（本地规则+RAG）' }}
                </el-tag>
              </div>
              <div class="status-hint">
                API Key：{{ status?.api_key_configured ? '已配置' : '未配置（不展示明文）' }}
              </div>
            </div>

            <div class="status-card">
              <div class="status-label">API 地址</div>
              <div class="status-value mono">{{ status?.base_url || '—' }}</div>
              <div class="status-hint">模型：{{ status?.model_name || '—' }}</div>
            </div>

            <div class="status-card">
              <div class="status-label">联网检索（DeepResearch）</div>
              <div class="status-value">
                <el-tag :type="status?.deep_search_available ? 'success' : 'warning'">
                  {{ status?.deep_search_available ? '已开启可用' : (status?.deep_search_enabled ? '已开启但不可用' : '已关闭') }}
                </el-tag>
              </div>
              <div class="status-hint">
                Tavily Key：{{ status?.deep_search_key_configured ? '已配置' : '未配置' }} ·
                RAG top_k={{ status?.rag_top_k }}
              </div>
              <div v-if="status?.deep_search_issue" class="status-warn">
                {{ status.deep_search_issue }}
              </div>
            </div>

            <div class="status-card">
              <div class="status-label">知识库</div>
              <div class="status-value">{{ metrics?.knowledge_chunks ?? '—' }} 个知识块</div>
              <div class="status-hint">{{ status?.knowledge_base || '本地 Markdown' }}</div>
            </div>
          </div>

          <div class="metrics-grid">
            <div class="metric">
              <div class="metric-value">{{ metrics?.sessions ?? 0 }}</div>
              <div class="metric-label">会话</div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ metrics?.messages ?? 0 }}</div>
              <div class="metric-label">消息</div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ metrics?.encounters ?? 0 }}</div>
              <div class="metric-label">问诊记录</div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ metrics?.appointments ?? 0 }}</div>
              <div class="metric-label">预约</div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ metrics?.departments ?? 0 }}</div>
              <div class="metric-label">科室</div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ metrics?.reports ?? 0 }}</div>
              <div class="metric-label">报告</div>
            </div>
          </div>

          <div class="agent-line">
            <span class="agent-label">Agent 链路：</span>
            <el-tag
              v-for="a in metrics?.agents || []"
              :key="a"
              size="small"
              effect="plain"
              class="agent-tag"
            >
              {{ a }}
            </el-tag>
          </div>

          <div class="danger-zone">
            <div>
              <div class="danger-title">数据管理</div>
              <div class="danger-hint">
                一键清空 sessions / messages / encounters / appointments 四张表的全部数据
              </div>
            </div>
            <el-button type="danger" :loading="clearing" @click="onClearAll">
              一键清空全部数据
            </el-button>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="tl('settings.health')">
        <HealthProfile />
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<style scoped>
.setting-section {
  max-width: 520px;
  padding: 12px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.setting-label {
  font-size: 14px;
  color: var(--text-main);
  font-weight: 600;
}

.status-area {
  padding-top: 8px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.status-card {
  background: var(--bg-soft);
  border-radius: 10px;
  padding: 16px 18px;
}

.status-label {
  font-size: 13px;
  color: var(--text-sub);
}

.status-value {
  margin-top: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
  word-break: break-all;
}

.status-value.mono {
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
}

.status-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.status-warn {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #fdf6ec;
  color: #b88230;
  font-size: 12px;
  line-height: 1.6;
  word-break: break-all;
}

html.dark .status-warn {
  background: #2e2618;
  color: #d8a75a;
}

.metrics-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 12px;
}

.metric {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  color: #0f766e;
}

.metric-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.agent-line {
  margin-top: 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.agent-label {
  font-size: 13px;
  color: var(--text-sub);
}

.agent-tag {
  font-size: 11px;
}

.danger-zone {
  margin-top: 22px;
  padding: 16px 18px;
  border: 1px solid #fbc4c4;
  border-radius: 10px;
  background: #fef0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

html.dark .danger-zone {
  background: #2b1a1a;
  border-color: #5c2b2b;
}

.danger-title {
  font-size: 14px;
  font-weight: 600;
  color: #f56c6c;
}

.danger-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-sub);
}
</style>
