<script setup>
import { ref, nextTick, computed } from 'vue'
import { useRoute } from 'vue-router'
import { consultationApi, medicationApi } from '../api'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()
const route = useRoute()
const messages = ref([])
const input = ref('')
const sending = ref(false)
const enableDeepSearch = ref(true)
const chatBody = ref(null)

// 规格书 3.3：用药咨询场景固定走 medication 入口，前端展示“建议咨询科室”横幅
const isMedication = computed(() => route.path === '/medication')
const sceneTitle = computed(() => (isMedication.value ? '用药咨询' : '线上问诊'))
const placeholder = computed(() =>
  isMedication.value
    ? '请输入药品/症状/剂量/合并用药信息，例如：布洛芬和感冒灵能一起吃吗'
    : '请输入症状描述，例如：发热两天，咳嗽有黄痰…'
)

const riskMeta = {
  low: { type: 'success', label: '低风险' },
  medium: { type: 'warning', label: '中风险' },
  high: { type: 'danger', label: '高风险' },
}

function riskTag(level) {
  return riskMeta[level] || { type: 'info', label: level || '未知' }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatBody.value) {
      chatBody.value.scrollTop = chatBody.value.scrollHeight
    }
  })
}

async function send() {
  const text = input.value.trim()
  if (!text || sending.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  sending.value = true
  scrollToBottom()

  try {
    const payload = {
      message: text,
      session_id: session.sessionId || null,
      user_id: session.userId,
      enable_deep_search: enableDeepSearch.value,
    }
    const api = isMedication.value ? medicationApi : consultationApi
    const { data } = await api(payload)
    if (data.session_id) session.setSessionId(data.session_id)
    messages.value.push({
      role: 'assistant',
      content: data.answer,
      department: data.recommended_department,
      riskLevel: data.risk_level,
      evidence: data.evidence || [],
      redFlags: data.red_flags || [],
      followUps: data.follow_up_questions || [],
      disclaimer: data.disclaimer,
    })
  } catch (e) {
    // 规格书 3.2：失败信息以助手气泡呈现
    messages.value.push({
      role: 'assistant',
      content: '请求失败：' + (e?.response?.data?.detail || e?.message || '未知错误'),
      failed: true,
    })
  } finally {
    sending.value = false
    scrollToBottom()
  }
}
</script>

<template>
  <div class="chat">
    <!-- 规格书 3.3：用药咨询“建议咨询科室”横幅 -->
    <div v-if="isMedication" class="dept-banner">
      <span class="banner-label">建议咨询科室</span>
      <span class="banner-value">药学门诊</span>
      <span class="banner-hint">药物相互作用、重复用药、禁忌与特殊人群用药请咨询药师</span>
    </div>

    <div class="chat-body" ref="chatBody">
      <div v-if="!messages.length" class="empty">
        <p>{{ isMedication ? '你好，我是诊小通的药学咨询助手。' : '你好，我是诊小通。' }}</p>
        <p v-if="isMedication">请描述药品名称、用法或合并用药情况，我会给出用药安全参考（不提供处方剂量）。</p>
        <p v-else>描述你的症状，我会帮你推荐挂号科室、评估风险并给出就医参考。</p>
      </div>

      <div
        v-for="(m, i) in messages"
        :key="i"
        class="msg"
        :class="m.role"
      >
        <div class="bubble">
          <div class="text" :class="{ failed: m.failed }">{{ m.content }}</div>

          <div v-if="m.role === 'assistant' && (m.department || m.riskLevel)" class="meta">
            <el-tag v-if="m.department" type="primary" effect="plain">
              推荐科室：{{ m.department }}
            </el-tag>
            <el-tag v-if="m.riskLevel" :type="riskTag(m.riskLevel).type" effect="plain">
              {{ riskTag(m.riskLevel).label }}
            </el-tag>
          </div>

          <div v-if="m.redFlags && m.redFlags.length" class="red-flags">
            <span class="rf-title">红旗信号：</span>
            <el-tag v-for="rf in m.redFlags" :key="rf" type="danger" size="small" effect="plain">
              {{ rf }}
            </el-tag>
          </div>

          <div v-if="m.followUps && m.followUps.length" class="follow-ups">
            <span class="fu-title">建议补充：</span>
            <span class="fu-item" v-for="q in m.followUps" :key="q">{{ q }}</span>
          </div>

          <el-collapse v-if="m.role === 'assistant' && m.evidence && m.evidence.length" class="evidence">
            <el-collapse-item :title="'参考依据（' + m.evidence.length + '）'">
              <ul>
                <li v-for="(ev, j) in m.evidence" :key="j">
                  <b>{{ ev.title }}</b>
                  <span class="src" v-if="ev.source">{{ ev.source }}</span>
                </li>
              </ul>
            </el-collapse-item>
          </el-collapse>

          <div v-if="m.role === 'assistant' && m.disclaimer" class="disclaimer">
            {{ m.disclaimer }}
          </div>
        </div>
      </div>

      <div v-if="sending" class="msg assistant">
        <div class="bubble typing">正在思考，请稍候…</div>
      </div>
    </div>

    <div class="chat-input">
      <el-input
        v-model="input"
        type="textarea"
        :rows="3"
        resize="none"
        :placeholder="placeholder"
        @keydown.enter.exact.prevent="send"
      />
      <div class="actions">
        <el-switch v-model="enableDeepSearch" active-text="联网深搜" />
        <el-button type="primary" :loading="sending" @click="send">
          发送{{ isMedication ? '（用药咨询）' : '' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat {
  height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border-radius: 8px;
  overflow: hidden;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.empty {
  text-align: center;
  color: var(--text-muted);
  margin-top: 80px;
  line-height: 2;
}

.msg {
  display: flex;
  margin-bottom: 16px;
}

.msg.user {
  justify-content: flex-end;
}

.msg.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 72%;
  padding: 12px 16px;
  border-radius: 8px;
  line-height: 1.7;
  word-break: break-word;
}

.msg.user .bubble {
  background: #1890ff;
  color: #fff;
}

.msg.assistant .bubble {
  background: var(--bg-chat-ai);
  color: var(--text-body);
}

.typing {
  color: var(--text-muted);
}

.text.failed {
  color: #f56c6c;
}

/* —— 用药咨询：建议咨询科室横幅 —— */
.dept-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: linear-gradient(90deg, #0f766e, #14b8a6);
  color: #fff;
}

.dept-banner .banner-label {
  font-size: 12px;
  opacity: 0.85;
}

.dept-banner .banner-value {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 1px;
}

.dept-banner .banner-hint {
  margin-left: auto;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
}

.red-flags {
  margin-top: 8px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
}

.rf-title {
  color: #f56c6c;
  font-weight: 600;
}

.follow-ups {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-sub);
}

.fu-title {
  font-weight: 600;
}

.fu-item::after {
  content: '；';
}

.fu-item:last-child::after {
  content: '';
}

.meta {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

.evidence {
  margin-top: 8px;
  border: none;
}

.evidence ul {
  margin: 0;
  padding-left: 18px;
  color: var(--text-sub);
  font-size: 13px;
}

.evidence .src {
  display: block;
  color: var(--text-muted);
  font-size: 12px;
  word-break: break-all;
}

.disclaimer {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-faint);
}

.chat-input {
  border-top: 1px solid var(--border);
  padding: 12px 16px;
}

.actions {
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
