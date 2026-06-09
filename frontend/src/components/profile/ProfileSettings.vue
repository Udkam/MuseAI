<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { MuseumCard } from '../../design-system/components/index.js'
import { api } from '../../api/index.js'

const loading = ref(false)
const saving = ref(false)

const interestOptions = [
  { label: '器物工艺', value: 'craft' },
  { label: '聚落空间', value: 'settlement' },
  { label: '社会组织', value: 'social_structure' },
  { label: '精神文化', value: 'spiritual_culture' },
  { label: '史前生活', value: 'daily_life' },
  { label: '研学记录', value: 'study_notes' },
]

const knowledgeLevels = [
  { label: '入门观察', value: 'beginner' },
  { label: '进阶推理', value: 'intermediate' },
  { label: '研究分析', value: 'expert' },
]

const narrativePreferences = [
  { label: '清晰讲解', value: 'explain' },
  { label: '证据推理', value: 'evidence' },
  { label: '研学任务', value: 'study' },
  { label: '反思追问', value: 'reflection' },
]

const profile = ref({
  interests: [],
  knowledge_level: 'beginner',
  narrative_preference: 'explain',
  reflection_depth: 3,
})

async function loadProfile() {
  loading.value = true

  try {
    const result = await api.profile.get()

    if (result.ok && result.data) {
      profile.value = {
        interests: result.data.interests || [],
        knowledge_level: result.data.knowledge_level || 'beginner',
        narrative_preference: result.data.narrative_preference || 'explain',
        reflection_depth: result.data.reflection_depth || 3,
      }
    } else {
      ElMessage.error(`加载个人偏好失败：${result.data?.detail || `HTTP ${result.status}`}`)
    }
  } catch (error) {
    ElMessage.error(`加载个人偏好失败：${error.message}`)
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  saving.value = true

  try {
    const result = await api.profile.update(profile.value)

    if (result.ok) {
      ElMessage.success('个人偏好已保存')
    } else {
      ElMessage.error(`保存失败：${result.data?.detail || `HTTP ${result.status}`}`)
    }
  } catch (error) {
    ElMessage.error(`保存失败：${error.message}`)
  } finally {
    saving.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <div class="profile-settings" v-loading="loading">
    <header class="profile-hero">
      <p class="eyebrow">半坡导览偏好</p>
      <h1>个人设置</h1>
      <p>这里用于 Web 端导览偏好；小程序端仍以三步问卷和四身份结果为主。</p>
    </header>

    <el-form label-position="top" :model="profile" class="profile-form">
      <MuseumCard title="关注方向" subtitle="选择你希望 MuseAI 优先展开的半坡主题">
        <el-form-item label="感兴趣的主题">
          <el-checkbox-group v-model="profile.interests" class="interest-group">
            <el-checkbox v-for="option in interestOptions" :key="option.value" :label="option.value">
              {{ option.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </MuseumCard>

      <MuseumCard title="讲解深度" subtitle="影响 Web 端回答的解释密度和推理方式">
        <el-form-item label="知识水平">
          <el-radio-group v-model="profile.knowledge_level">
            <el-radio v-for="level in knowledgeLevels" :key="level.value" :label="level.value">
              {{ level.label }}
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="叙事风格偏好">
          <el-radio-group v-model="profile.narrative_preference">
            <el-radio v-for="preference in narrativePreferences" :key="preference.value" :label="preference.value">
              {{ preference.label }}
            </el-radio>
          </el-radio-group>
        </el-form-item>
      </MuseumCard>

      <MuseumCard title="反思深度" subtitle="决定导览中的问题挑战强度">
        <el-form-item :label="`反思深度 (${profile.reflection_depth}/5)`">
          <el-slider v-model="profile.reflection_depth" :min="1" :max="5" :step="1" show-stops />
          <div class="slider-labels">
            <span>轻量</span>
            <span>深入</span>
          </div>
        </el-form-item>
      </MuseumCard>

      <div class="profile-actions">
        <el-button
          data-testid="profile-save"
          type="primary"
          :loading="saving"
          @click="saveProfile"
        >
          保存设置
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<style scoped>
.profile-settings {
  max-width: 840px;
  margin: 0 auto;
  padding: 8px 0 24px;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--color-accent);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
}

.profile-hero h1 {
  margin: 0;
  font-family: var(--font-family-base);
  font-size: clamp(24px, 2.8vw, 32px);
}

.profile-hero p:last-child {
  max-width: 620px;
  margin: 8px 0 0;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.profile-form {
  display: grid;
  gap: 16px;
  margin-top: 16px;
}

.interest-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 5px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.profile-actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 767px) {
  .profile-settings {
    padding-bottom: 12px;
  }

  .profile-actions {
    justify-content: stretch;
  }

  .profile-actions .el-button {
    width: 100%;
  }
}
</style>
