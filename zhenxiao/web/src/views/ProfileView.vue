<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getProfile, upsertProfile } from '../api'
import { useSessionStore } from '../stores/session'
import { useSettingsStore } from '../stores/settings'
import { t } from '../i18n'

const session = useSessionStore()
const settings = useSettingsStore()
const form = reactive({
  age: null,
  gender: '',
  chronic_diseases: '',
  allergy_history: '',
  medication_history: '',
})
const loading = ref(false)

function tl(key) {
  return t(settings.language, key)
}

async function load() {
  loading.value = true
  try {
    const { data } = await getProfile(session.userId)
    Object.assign(form, data)
  } catch (e) {
    if (e?.response?.status !== 404) {
      ElMessage.error(tl('profile.loadFailed') + '：' + (e?.message || ''))
    }
  } finally {
    loading.value = false
  }
}

async function save() {
  try {
    await upsertProfile(session.userId, form)
    ElMessage.success(tl('profile.saved'))
  } catch (e) {
    ElMessage.error(tl('profile.saveFailed') + '：' + (e?.message || ''))
  }
}

onMounted(load)
</script>

<template>
  <div class="profile" v-loading="loading">
    <el-form :model="form" label-width="120px" class="form">
      <el-form-item :label="tl('profile.age')">
        <el-input-number v-model="form.age" :min="0" :max="150" />
      </el-form-item>
      <el-form-item :label="tl('profile.gender')">
        <el-radio-group v-model="form.gender">
          <el-radio value="男">{{ tl('profile.male') }}</el-radio>
          <el-radio value="女">{{ tl('profile.female') }}</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item :label="tl('profile.chronic')">
        <el-input v-model="form.chronic_diseases" type="textarea" :rows="2" placeholder="高血压、糖尿病" />
      </el-form-item>
      <el-form-item :label="tl('profile.allergy')">
        <el-input v-model="form.allergy_history" type="textarea" :rows="2" placeholder="青霉素过敏" />
      </el-form-item>
      <el-form-item :label="tl('profile.medication')">
        <el-input v-model="form.medication_history" type="textarea" :rows="2" placeholder="长期服用的药物" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="save">{{ tl('profile.save') }}</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped>
.profile {
  padding-top: 8px;
}

.form {
  max-width: 520px;
}
</style>
