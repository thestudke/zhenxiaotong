<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listReports, interpretReport } from '../api'

const reports = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const interpreting = ref(false)
const selectedReport = ref(null)
const current = ref(null)

const riskMeta = {
  low: { type: 'success', label: '低风险' },
  medium: { type: 'warning', label: '中风险' },
  high: { type: 'danger', label: '高风险' },
}

function riskTag(level) {
  return riskMeta[level] || { type: 'info', label: level || '未知' }
}

function flagType(flag) {
  return flag === '正常' ? 'success' : 'danger'
}

async function load() {
  loading.value = true
  try {
    const { data } = await listReports()
    reports.value = data
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.message || ''))
  } finally {
    loading.value = false
  }
}

async function openInterpret(report) {
  selectedReport.value = report
  current.value = null
  dialogVisible.value = true
  interpreting.value = true
  try {
    const { data } = await interpretReport(report.id)
    current.value = data
  } catch (e) {
    ElMessage.error('解读失败：' + (e?.response?.data?.detail || e?.message || ''))
    dialogVisible.value = false
  } finally {
    interpreting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <el-card v-for="r in reports" :key="r.id" class="report-card">
      <template #header>
        <div class="report-header">
          <div class="report-title">
            <span class="name">{{ r.name }}</span>
            <el-tag :type="riskTag(r.risk_level).type" effect="plain">
              {{ riskTag(r.risk_level).label }}
            </el-tag>
            <span class="dept">{{ r.department }}</span>
          </div>
          <div class="report-actions">
            <span class="date">{{ r.exam_date }}</span>
            <el-button type="primary" size="small" @click="openInterpret(r)">AI 解读</el-button>
          </div>
        </div>
      </template>

      <el-table :data="r.items" size="small">
        <el-table-column prop="name" label="指标" min-width="180" />
        <el-table-column prop="value" label="结果" width="160" />
        <el-table-column prop="unit" label="单位" width="100" />
        <el-table-column prop="reference_range" label="参考范围" min-width="120" />
        <el-table-column label="判定" width="90">
          <template #default="{ row }">
            <el-tag :type="flagType(row.flag)" size="small">{{ row.flag }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="selectedReport ? selectedReport.name + ' · AI 解读' : 'AI 解读'"
      width="560px"
    >
      <div v-if="interpreting" class="interpreting">正在解读，请稍候…</div>
      <div v-else-if="current">
        <div class="analysis">
          <span class="analysis-label">异常分析：</span>{{ current.analysis }}
        </div>
        <div class="interpretation">{{ current.interpretation }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.report-card {
  margin-bottom: 16px;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.report-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.report-title .name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

.report-title .dept {
  font-size: 13px;
  color: var(--text-sub);
}

.report-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.report-actions .date {
  font-size: 13px;
  color: var(--text-muted);
}

.interpreting {
  text-align: center;
  color: var(--text-muted);
  padding: 30px 0;
}

.analysis {
  font-size: 13px;
  color: var(--text-sub);
  line-height: 1.7;
  margin-bottom: 14px;
  padding: 10px 12px;
  background: var(--bg-soft);
  border-radius: 8px;
}

.analysis-label {
  font-weight: 600;
  color: var(--text-main);
}

.interpretation {
  white-space: pre-wrap;
  line-height: 1.8;
  color: var(--text-body);
  font-size: 14px;
}
</style>
