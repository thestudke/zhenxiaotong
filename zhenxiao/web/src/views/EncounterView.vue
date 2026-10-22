<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listRecords } from '../api'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()
const rows = ref([])
const loading = ref(false)
const days = ref(7)
const scene = ref('')
const dialogVisible = ref(false)
const current = ref(null)

// 规格书 3.5：近 7/30/180 天
const dayOptions = [
  { label: '近 7 天', value: 7 },
  { label: '近 30 天', value: 30 },
  { label: '近 180 天', value: 180 },
]

const sceneOptions = [
  { label: '全部', value: '' },
  { label: '智能分诊', value: 'triage' },
  { label: '线上问诊', value: 'consultation' },
  { label: '用药咨询', value: 'medication' },
]

const riskMeta = {
  low: { type: 'success', label: '低风险' },
  medium: { type: 'warning', label: '中风险' },
  high: { type: 'danger', label: '高风险' },
}

function riskTag(level) {
  return riskMeta[level] || { type: 'info', label: level || '未知' }
}

const sceneType = {
  triage: 'primary',
  consultation: 'success',
  medication: 'warning',
}

function fmtTime(s) {
  return s ? s.replace('T', ' ').slice(0, 16) : ''
}

const countByScene = computed(() => {
  const acc = { triage: 0, consultation: 0, medication: 0 }
  rows.value.forEach((r) => {
    if (acc[r.scene] !== undefined) acc[r.scene] += 1
  })
  return acc
})

async function load() {
  loading.value = true
  try {
    const params = { user_id: session.userId, days: days.value }
    if (scene.value) params.scene = scene.value
    const { data } = await listRecords(params)
    rows.value = data.records || []
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e?.message || ''))
  } finally {
    loading.value = false
  }
}

function openDetail(row) {
  current.value = row
  dialogVisible.value = true
}

onMounted(load)
</script>

<template>
  <div class="records">
    <div class="stats-grid">
      <div class="stat-card">
        <div class="card-label">智能分诊</div>
        <div class="card-value">{{ countByScene.triage }}</div>
      </div>
      <div class="stat-card">
        <div class="card-label">线上问诊</div>
        <div class="card-value">{{ countByScene.consultation }}</div>
      </div>
      <div class="stat-card">
        <div class="card-label">用药咨询</div>
        <div class="card-value">{{ countByScene.medication }}</div>
      </div>
    </div>

    <el-card>
      <template #header>
        <div class="header">
          <span>问诊记录</span>
          <div class="filters">
            <el-radio-group v-model="days" size="small" @change="load">
              <el-radio-button v-for="d in dayOptions" :key="d.value" :value="d.value">
                {{ d.label }}
              </el-radio-button>
            </el-radio-group>
            <el-select v-model="scene" size="small" style="width: 130px" @change="load">
              <el-option v-for="s in sceneOptions" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </div>
        </div>
      </template>

      <div v-loading="loading" class="card-list">
        <el-empty v-if="!loading && !rows.length" description="该时间范围内暂无记录" />

        <div v-for="row in rows" :key="row.id" class="record-card" @click="openDetail(row)">
          <div class="record-head">
            <el-tag :type="sceneType[row.scene] || 'info'" size="small" effect="plain">
              {{ row.scene_label || row.scene }}
            </el-tag>
            <el-tag :type="riskTag(row.risk_level).type" size="small" effect="plain">
              {{ riskTag(row.risk_level).label }}
            </el-tag>
            <span class="dept" v-if="row.department">{{ row.department }}</span>
            <span class="time">{{ fmtTime(row.created_at) }}</span>
          </div>
          <div class="record-chief">{{ row.chief_complaint }}</div>
          <div class="record-summary">{{ row.summary }}</div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" title="记录详情" width="640px">
      <div v-if="current" class="detail">
        <div class="detail-row">
          <span class="label">场景</span>
          <span>{{ current.scene_label || current.scene }}</span>
        </div>
        <div class="detail-row">
          <span class="label">风险等级</span>
          <el-tag :type="riskTag(current.risk_level).type" size="small" effect="plain">
            {{ riskTag(current.risk_level).label }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="label">推荐科室</span>
          <span>{{ current.department || '—' }}</span>
        </div>
        <div class="detail-row">
          <span class="label">时间</span>
          <span>{{ fmtTime(current.created_at) }}</span>
        </div>
        <div class="detail-block">
          <div class="label">主诉</div>
          <div class="block-body">{{ current.chief_complaint }}</div>
        </div>
        <div class="detail-block">
          <div class="label">完整摘要</div>
          <div class="block-body">{{ current.summary }}</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--bg-card);
  border-radius: 10px;
  padding: 16px 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.card-label {
  font-size: 13px;
  color: var(--text-sub);
}

.card-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-main);
  margin-top: 6px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.filters {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-list {
  min-height: 120px;
}

.record-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
  background: var(--bg-soft);
}

.record-card:hover {
  border-color: #14b8a6;
  box-shadow: 0 2px 8px rgba(20, 184, 166, 0.15);
}

.record-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.record-head .dept {
  color: #0f766e;
  font-weight: 600;
}

.record-head .time {
  margin-left: auto;
}

.record-chief {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.record-summary {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-sub);
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  font-size: 14px;
}

.detail-row .label {
  width: 80px;
  color: var(--text-muted);
}

.detail-block {
  margin-top: 12px;
}

.detail-block .label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.block-body {
  background: var(--bg-soft);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-body);
  white-space: pre-wrap;
}
</style>
