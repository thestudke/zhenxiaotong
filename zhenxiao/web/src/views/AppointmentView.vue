<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listDepartments,
  getSchedule,
  listAppointments,
  createAppointment,
  cancelAppointment,
} from '../api'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()

const departments = ref([])
const schedule = ref([])
const appointments = ref([])
const activeDept = ref('')
const loadingSchedule = ref(false)
const loadingAppointments = ref(false)
const submitting = ref(false)
const activeDay = ref('')

const bookForm = reactive({
  doctor: '',
  doctor_title: '',
  visit_date: '',
  period: '',
  time_slot: '',
  remaining: 0,
})

const currentDay = computed(
  () => schedule.value.find((d) => d.visit_date === activeDay.value) || schedule.value[0] || null
)

function periodLabel(p) {
  return p === '上午' ? '上午' : '下午'
}

function remainingType(n) {
  if (n <= 0) return 'danger'
  if (n <= 2) return 'warning'
  return 'success'
}

async function loadDepartments() {
  try {
    const { data } = await listDepartments()
    departments.value = data.departments || []
    if (!activeDept.value && departments.value.length) {
      activeDept.value = departments.value[0].name
    }
  } catch (e) {
    ElMessage.error('科室列表加载失败：' + (e?.message || ''))
  }
}

async function loadSchedule() {
  if (!activeDept.value) return
  loadingSchedule.value = true
  try {
    const { data } = await getSchedule({
      department: activeDept.value,
      user_id: session.userId,
    })
    schedule.value = data.days || []
    activeDay.value = schedule.value.length ? schedule.value[0].visit_date : ''
  } catch (e) {
    schedule.value = []
    ElMessage.error('排班加载失败：' + (e?.response?.data?.detail || e?.message || ''))
  } finally {
    loadingSchedule.value = false
  }
}

async function loadAppointments() {
  loadingAppointments.value = true
  try {
    const { data } = await listAppointments({ user_id: session.userId })
    appointments.value = data.appointments || []
  } catch (e) {
    ElMessage.error('预约列表加载失败：' + (e?.message || ''))
  } finally {
    loadingAppointments.value = false
  }
}

async function selectDepartment(name) {
  if (activeDept.value === name) return
  activeDept.value = name
  await loadSchedule()
}

function pickSlot(day, period, slot) {
  if (slot.remaining <= 0) {
    ElMessage.warning('该时段号源已约满')
    return
  }
  Object.assign(bookForm, {
    doctor: slot.doctor,
    doctor_title: slot.doctor_title,
    visit_date: day.visit_date,
    period: period.period,
    time_slot: slot.time_slot,
    remaining: slot.remaining,
  })
}

async function submit() {
  if (!bookForm.visit_date || !bookForm.time_slot) {
    ElMessage.warning('请先在排班表中选择号源')
    return
  }
  submitting.value = true
  try {
    const { data } = await createAppointment({
      user_id: session.userId,
      department: activeDept.value,
      doctor: bookForm.doctor,
      doctor_title: bookForm.doctor_title,
      visit_date: bookForm.visit_date,
      period: bookForm.period,
      time_slot: bookForm.time_slot,
    })
    if (data.created) {
      ElMessage.success(`预约成功，预约号 ${data.appointment?.no || data.appointment_id}`)
    } else {
      ElMessage.info(`该号源已预约过，预约号 ${data.appointment?.no || data.appointment_id}`)
    }
    bookForm.time_slot = ''
    await Promise.all([loadSchedule(), loadAppointments()])
  } catch (e) {
    ElMessage.error('预约失败：' + (e?.response?.data?.detail || e?.message || ''))
  } finally {
    submitting.value = false
  }
}

async function cancel(row) {
  try {
    await ElMessageBox.confirm(
      `确认取消 ${row.visit_date} ${row.period} ${row.time_slot} 的预约？`,
      '取消预约',
      { type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await cancelAppointment(row.id, { user_id: session.userId })
    ElMessage.success('已取消预约')
    await Promise.all([loadSchedule(), loadAppointments()])
  } catch (e) {
    ElMessage.error('取消失败：' + (e?.response?.data?.detail || e?.message || ''))
  }
}

function fmtTime(s) {
  return s ? s.replace('T', ' ').slice(0, 16) : ''
}

onMounted(async () => {
  await loadDepartments()
  await Promise.all([loadSchedule(), loadAppointments()])
})
</script>

<template>
  <div class="appointment">
    <!-- 科室选择（规格书 3.1：从系统科室列表选取） -->
    <el-card class="dept-card">
      <template #header>选择科室</template>
      <div class="dept-grid">
        <div
          v-for="d in departments"
          :key="d.name"
          class="dept-chip"
          :class="{ active: activeDept === d.name }"
          @click="selectDepartment(d.name)"
        >
          {{ d.name }}
        </div>
      </div>
    </el-card>

    <!-- 7 天排班号源 -->
    <el-card class="schedule-card">
      <template #header>
        <div class="header">
          <span>{{ activeDept || '科室' }} · 未来 7 天号源</span>
          <el-button size="small" @click="loadSchedule">刷新</el-button>
        </div>
      </template>

      <div v-loading="loadingSchedule">
        <div class="day-tabs">
          <div
            v-for="d in schedule"
            :key="d.visit_date"
            class="day-tab"
            :class="{ active: activeDay === d.visit_date }"
            @click="activeDay = d.visit_date"
          >
            <div class="day-week">{{ d.weekday }}</div>
            <div class="day-date">{{ d.visit_date.slice(5) }}</div>
            <div class="day-remain">
              余 {{ d.periods.reduce((s, p) => s + p.remaining, 0) }}
            </div>
          </div>
        </div>

        <div v-if="currentDay" class="periods">
          <div v-for="p in currentDay.periods" :key="p.period" class="period-block">
            <div class="period-title">
              <span>{{ periodLabel(p.period) }}</span>
              <span class="period-remain">余号 {{ p.remaining }} / {{ p.total }}</span>
            </div>
            <div class="slot-grid">
              <div
                v-for="s in p.slots"
                :key="s.time_slot"
                class="slot"
                :class="{
                  disabled: s.remaining <= 0,
                  picked:
                    bookForm.visit_date === currentDay.visit_date &&
                    bookForm.period === p.period &&
                    bookForm.time_slot === s.time_slot,
                }"
                @click="pickSlot(currentDay, p, s)"
              >
                <div class="slot-time">{{ s.time_slot }}</div>
                <div class="slot-doctor">{{ s.doctor }} · {{ s.doctor_title }}</div>
                <el-tag :type="remainingType(s.remaining)" size="small" effect="plain">
                  {{ s.remaining > 0 ? `余 ${s.remaining}` : '已满' }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="book-bar">
        <span v-if="bookForm.time_slot" class="picked-info">
          已选：{{ bookForm.visit_date }} {{ bookForm.period }} {{ bookForm.time_slot }} ·
          {{ bookForm.doctor }}（余 {{ bookForm.remaining }}）
        </span>
        <span v-else class="picked-info muted">请在上方排班中选择一个号源</span>
        <el-button type="primary" :loading="submitting" @click="submit">确认预约</el-button>
      </div>
    </el-card>

    <!-- 我的预约 -->
    <el-card>
      <template #header>我的预约</template>
      <el-table :data="appointments" v-loading="loadingAppointments" stripe>
        <el-table-column prop="no" label="预约号" width="110" />
        <el-table-column prop="department" label="科室" width="110" />
        <el-table-column prop="doctor" label="医生" width="100" />
        <el-table-column prop="doctor_title" label="职称" width="120" />
        <el-table-column prop="visit_date" label="日期" width="120" />
        <el-table-column prop="period" label="时段" width="80" />
        <el-table-column prop="time_slot" label="具体时间" width="130" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '已预约' ? 'success' : 'info'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              v-if="row.status === '已预约'"
              type="danger"
              link
              @click="cancel(row)"
            >
              取消预约
            </el-button>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.appointment {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dept-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.dept-chip {
  padding: 8px 16px;
  border-radius: 20px;
  background: var(--bg-soft);
  border: 1px solid var(--border);
  font-size: 13px;
  color: var(--text-body);
  cursor: pointer;
  transition: all 0.2s;
}

.dept-chip:hover {
  border-color: #14b8a6;
  color: #0f766e;
}

.dept-chip.active {
  background: linear-gradient(90deg, #0f766e, #14b8a6);
  border-color: transparent;
  color: #fff;
  font-weight: 600;
}

.day-tabs {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
}

.day-tab {
  text-align: center;
  padding: 10px 4px;
  border-radius: 8px;
  background: var(--bg-soft);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all 0.2s;
}

.day-tab.active {
  border-color: #14b8a6;
  background: #f0fdfa;
}

html.dark .day-tab.active {
  background: #14312e;
}

.day-week {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.day-date {
  font-size: 12px;
  color: var(--text-sub);
  margin-top: 2px;
}

.day-remain {
  font-size: 11px;
  color: #0f766e;
  margin-top: 4px;
}

.periods {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.period-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 10px;
}

.period-remain {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 400;
}

.slot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.slot {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  background: var(--bg-card);
  transition: all 0.2s;
}

.slot:hover {
  border-color: #14b8a6;
}

.slot.picked {
  border-color: #1e40af;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.slot.disabled {
  opacity: 0.55;
  cursor: not-allowed;
  background: var(--bg-soft);
}

.slot-time {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
}

.slot-doctor {
  font-size: 12px;
  color: var(--text-sub);
  margin: 4px 0 6px;
}

.book-bar {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.picked-info {
  font-size: 13px;
  color: var(--text-body);
}

.picked-info.muted,
.muted {
  color: var(--text-muted);
}
</style>
