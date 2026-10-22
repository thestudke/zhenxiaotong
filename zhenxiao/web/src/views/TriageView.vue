<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { triageApi, listRecords, getMetrics } from '../api'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()

const form = reactive({
  age: null,
  gender: '',
  history: '',
  symptoms: '',
})

const loading = ref(false)
const result = ref(null)
const trace = ref([])
const encounterCount = ref(0)
const reportCount = ref(0)

const stats = computed(() => [
  { title: '服务模块', value: '7', desc: 'Router / Context / RAG / Research / Reasoning / Formatter / Safety' },
  { title: '问诊记录', value: String(encounterCount.value), desc: '累计分诊、问诊与用药记录' },
  { title: '报告查询', value: String(reportCount.value), desc: '内置检验/检查报告' },
])

const riskMeta = {
  low: { label: '低风险', color: '#67c23a' },
  medium: { label: '中风险', color: '#e6a23c' },
  high: { label: '高风险', color: '#f56c6c' },
}

const riskInfo = computed(() => {
  if (!result.value) return null
  return riskMeta[result.value.risk_level] || { label: result.value.risk_level || '未知', color: '#909399' }
})

async function loadCount() {
  try {
    const [{ data }, m] = await Promise.all([
      listRecords({ user_id: session.userId, days: 365 }),
      getMetrics(),
    ])
    encounterCount.value = data.total || (data.records || []).length
    reportCount.value = m.data.reports || 0
  } catch (e) {
    /* ignore */
  }
}

async function submit() {
  if (!form.symptoms.trim()) {
    ElMessage.warning('请先描述症状')
    return
  }
  loading.value = true
  result.value = null
  trace.value = []
  try {
    const { data } = await triageApi({
      message: form.symptoms.trim(),
      session_id: session.sessionId || null,
      user_id: session.userId,
      patient_context: {
        age: form.age,
        gender: form.gender,
        chronic_diseases: form.history,
      },
      enable_deep_search: true,
    })
    if (data.session_id) session.setSessionId(data.session_id)
    result.value = data
    trace.value = data.trace || []
    loadCount()
  } catch (e) {
    ElMessage.error('生成失败：' + (e?.response?.data?.detail || e?.message || ''))
  } finally {
    loading.value = false
  }
}

onMounted(loadCount)
</script>

<template>
  <div class="triage">
    <!-- 顶部欢迎 Banner -->
    <div class="welcome-banner">
      <div>
        <h2>欢迎使用诊小通</h2>
        <p>智能分诊、在线问诊、用药咨询一站式服务</p>
      </div>
      <el-button class="banner-btn" @click="$refs.formPanel?.scrollIntoView({ behavior: 'smooth' })">
        快速问诊
      </el-button>
    </div>

    <!-- 数据统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="item in stats" :key="item.title">
        <div class="card-header">
          <span>{{ item.title }}</span>
          <span class="card-add">+</span>
        </div>
        <div class="card-value">{{ item.value }}</div>
        <div class="card-desc">{{ item.desc }}</div>
      </div>
    </div>

    <!-- 底部双栏 -->
    <div class="bottom-split">
      <!-- 左侧：智能分诊台表单 -->
      <div class="panel form-panel" ref="formPanel">
        <h3 class="panel-title">智能分诊台</h3>
        <el-form :model="form" label-position="top">
          <div class="form-row">
            <el-form-item label="年龄">
              <el-input-number v-model="form.age" :min="0" :max="150" :controls="false" placeholder="年龄" />
            </el-form-item>
            <el-form-item label="性别">
              <el-select v-model="form.gender" placeholder="请选择" clearable>
                <el-option label="男" value="男" />
                <el-option label="女" value="女" />
              </el-select>
            </el-form-item>
          </div>

          <el-form-item label="既往病史">
            <el-input v-model="form.history" placeholder="如：高血压、糖尿病、无" />
          </el-form-item>

          <el-form-item label="症状描述">
            <el-input
              v-model="form.symptoms"
              type="textarea"
              :rows="5"
              resize="none"
              placeholder="请详细描述您的症状，例如：发热两天，咳嗽有黄痰，体温 38.7 度…"
            />
          </el-form-item>

          <el-button class="gradient-btn" :loading="loading" @click="submit">
            生成分诊建议
          </el-button>
        </el-form>

        <!-- 风险指标卡片 -->
        <div v-if="result" class="result-area">
          <!-- 规格书 3.1：推荐科室以醒目渐变卡片展示 -->
          <div class="dept-banner">
            <div class="dept-banner-label">推荐挂号科室</div>
            <div class="dept-banner-value">{{ result.recommended_department || '待评估' }}</div>
            <div class="dept-banner-hint">请以系统科室列表为准，必要时可向导诊台咨询</div>
          </div>

          <div class="risk-cards">
            <div class="risk-card">
              <div class="risk-label">风险等级</div>
              <div class="risk-value" :style="{ color: riskInfo?.color }">{{ riskInfo?.label }}</div>
            </div>
            <div class="risk-card">
              <div class="risk-label">证据条数</div>
              <div class="risk-value">{{ (result.evidence || []).length }}</div>
            </div>
          </div>

          <div class="answer">{{ result.answer }}</div>

          <div v-if="result.red_flags && result.red_flags.length" class="info-block danger">
            <div class="info-title">红旗信号（需尽快线下就医）</div>
            <div class="tag-line">
              <el-tag v-for="rf in result.red_flags" :key="rf" type="danger" size="small" effect="plain">
                {{ rf }}
              </el-tag>
            </div>
          </div>

          <div v-if="result.health_advice && result.health_advice.length" class="info-block">
            <div class="info-title">健康建议</div>
            <ul>
              <li v-for="(a, i) in result.health_advice" :key="i">{{ a }}</li>
            </ul>
          </div>

          <div v-if="result.follow_up_questions && result.follow_up_questions.length" class="info-block">
            <div class="info-title">建议追问</div>
            <ul>
              <li v-for="(q, i) in result.follow_up_questions" :key="i">{{ q }}</li>
            </ul>
          </div>

          <div v-if="result.disclaimer" class="disclaimer">{{ result.disclaimer }}</div>
        </div>
      </div>

      <!-- 右侧：AI 思考链路 -->
      <div class="panel ai-panel">
        <h3 class="panel-title">分诊证据与 Agent 链路</h3>
        <div class="thinking-list">
          <div v-if="!trace.length && !loading" class="empty-trace">
            提交症状后，这里将展示每个 Agent 的思考链路与耗时
          </div>
          <div v-else-if="loading" class="empty-trace">正在推理…</div>

          <div class="thinking-card" v-for="(t, i) in trace" :key="i">
            <div class="step-header">
              <span class="step-dot"></span>
              Thinking {{ i + 1 }}
              <span class="step-duration" v-if="t.duration_ms">{{ t.duration_ms }}ms</span>
            </div>
            <div class="step-content">
              <strong>{{ t.agent }}</strong>
              <span v-if="t.action" class="step-action">· {{ t.action }}</span>
              <div v-if="t.detail" class="step-detail">{{ t.detail }}</div>
            </div>
          </div>
        </div>

        <!-- 参考依据 -->
        <div v-if="result && result.evidence && result.evidence.length" class="evidence-area">
          <div class="evidence-title">参考依据（{{ result.evidence.length }}）</div>
          <ul>
            <li v-for="(ev, i) in result.evidence" :key="i">
              <b>{{ ev.title || '未命名依据' }}</b>
              <span class="src" v-if="ev.source">{{ ev.source }}</span>
              <p class="content" v-if="ev.content">{{ ev.content.slice(0, 160) }}</p>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* —— 欢迎 Banner —— */
.welcome-banner {
  background: linear-gradient(90deg, #0f766e, #14b8a6);
  color: #fff;
  border-radius: 10px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.welcome-banner h2 {
  margin: 0;
  font-size: 20px;
}

.welcome-banner p {
  margin: 6px 0 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

.banner-btn {
  background: #fff;
  color: #0f766e;
  border: none;
  font-weight: 600;
}

/* —— 统计卡片 —— */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--bg-card);
  border-radius: 10px;
  padding: 18px 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-sub);
  font-size: 13px;
}

.card-add {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #f0fdfa;
  color: #0f766e;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.card-value {
  font-size: 30px;
  font-weight: 700;
  color: var(--text-main);
  margin: 8px 0 4px;
}

.card-desc {
  font-size: 12px;
  color: var(--text-muted);
}

/* —— 底部双栏 —— */
.bottom-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: start;
}

.panel {
  background: var(--bg-card);
  border-radius: 10px;
  padding: 20px 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.panel-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
}

/* —— 表单 —— */
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.gradient-btn {
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(90deg, #1e40af, #3b82f6);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  margin-top: 4px;
}

/* —— 结果区 —— */
.result-area {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

/* 规格书 3.1：推荐科室醒目渐变卡片 */
.dept-banner {
  background: linear-gradient(120deg, #1e40af, #14b8a6);
  color: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 14px;
  box-shadow: 0 4px 14px rgba(20, 184, 166, 0.25);
}

.dept-banner-label {
  font-size: 12px;
  opacity: 0.85;
}

.dept-banner-value {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 2px;
  margin: 6px 0;
}

.dept-banner-hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.82);
}

.info-block {
  margin-top: 12px;
}

.info-block.danger {
  background: #fef0f0;
  border-radius: 8px;
  padding: 10px 12px;
}

html.dark .info-block.danger {
  background: #2b1a1a;
}

.info-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-sub);
  margin-bottom: 6px;
}

.info-block.danger .info-title {
  color: #f56c6c;
}

.info-block ul {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: var(--text-body);
  line-height: 1.8;
}

.tag-line {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.risk-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.risk-card {
  background: var(--bg-soft);
  border-radius: 8px;
  padding: 12px 16px;
}

.risk-label {
  font-size: 12px;
  color: var(--text-muted);
}

.risk-value {
  font-size: 20px;
  font-weight: 700;
  margin-top: 4px;
  color: var(--text-main);
}

.answer {
  margin-top: 14px;
  line-height: 1.8;
  color: var(--text-body);
  white-space: pre-wrap;
}

.disclaimer {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-faint);
}

/* —— AI 链路 —— */
.thinking-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-trace {
  color: var(--text-faint);
  font-size: 13px;
  text-align: center;
  padding: 40px 0;
}

.thinking-card {
  border-left: 3px solid #3b82f6;
  background: var(--bg-soft);
  border-radius: 0 8px 8px 0;
  padding: 12px 16px;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3b82f6;
}

.step-duration {
  margin-left: auto;
  color: var(--text-faint);
}

.step-content {
  font-size: 14px;
  color: var(--text-body);
}

.step-action {
  color: var(--text-sub);
}

.step-detail {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.evidence-area {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.evidence-title {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 8px;
}

.evidence-area ul {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: var(--text-sub);
}

.evidence-area .src {
  display: block;
  font-size: 12px;
  color: var(--text-faint);
  word-break: break-all;
}

.evidence-area .content {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.6;
}
</style>
