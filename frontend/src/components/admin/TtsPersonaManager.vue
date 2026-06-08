<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Headset, RefreshRight, VideoPlay } from '@element-plus/icons-vue'
import { api } from '../../api/index.js'
import { BANPO_PERSONAS, TTS_VOICE_CONTRACT } from '../../constants/banpo.js'

const loading = ref(false)
const syncing = ref(false)
const previewLoading = ref(false)
const backendPersonas = ref([])
const previewAudioUrl = ref('')

const rows = computed(() => BANPO_PERSONAS.map((persona) => {
  const backend = findBackendPersona(persona.code)
  return {
    ...persona,
    backend,
    backendVoice: backend?.voice || '',
    backendDescription: backend?.voice_description || '',
    synced: backend?.voice === TTS_VOICE_CONTRACT.voice,
  }
}))

onMounted(fetchPersonas)

async function fetchPersonas() {
  loading.value = true
  try {
    const result = await api.admin.ttsPersonas.list()
    if (result.ok) {
      backendPersonas.value = result.data.personas || []
    } else {
      backendPersonas.value = []
      ElMessage.error(result.data?.detail || '获取语音角色失败')
    }
  } finally {
    loading.value = false
  }
}

function findBackendPersona(code) {
  const lower = code.toLowerCase()
  return backendPersonas.value.find((item) => {
    const key = String(item.key || '').toLowerCase()
    const persona = String(item.persona || '').toLowerCase()
    return key.endsWith(`_${lower}`) || persona === lower || item.code === code
  })
}

function buildPersonaPrompt(persona) {
  return [
    `【导览身份】${persona.name}`,
    `【回答角度】${persona.prompt}`,
    '【播报声线】统一使用冰糖声线。声音应清亮、自然、偏年轻女性；语速稍快但吐字清楚，避免中年男声、拖沓停顿和过度戏剧化。',
    '【播报方式】像现场导览员一样直接说明重点，不读出 Markdown 标记，不读出内部处理说明。',
  ].join('\n')
}

function buildUpdatePayload(persona) {
  return {
    content: buildPersonaPrompt(persona),
    voice: TTS_VOICE_CONTRACT.voice,
    voice_description: TTS_VOICE_CONTRACT.description,
    change_reason: '同步小程序 TTS 契约：只保留冰糖美少女声线',
  }
}

async function syncPersona(persona) {
  syncing.value = true
  try {
    const result = await api.admin.ttsPersonas.update(persona.code.toLowerCase(), buildUpdatePayload(persona))
    if (result.ok) {
      ElMessage.success(`${persona.name} 已同步为冰糖声线`)
      await fetchPersonas()
    } else {
      ElMessage.error(result.data?.detail || `${persona.name} 同步失败`)
    }
  } finally {
    syncing.value = false
  }
}

async function syncAll() {
  syncing.value = true
  let successCount = 0
  let failedCount = 0

  try {
    for (const persona of BANPO_PERSONAS) {
      const result = await api.admin.ttsPersonas.update(persona.code.toLowerCase(), buildUpdatePayload(persona))
      if (result.ok) {
        successCount += 1
      } else {
        failedCount += 1
      }
    }
    await fetchPersonas()
    if (failedCount) {
      ElMessage.warning(`已同步 ${successCount} 个角色，${failedCount} 个失败`)
    } else {
      ElMessage.success('四个导览身份已统一为冰糖声线')
    }
  } finally {
    syncing.value = false
  }
}

function playBase64Audio(base64, mimeType = 'audio/wav') {
  const bytes = atob(base64)
  const buffer = new Uint8Array(bytes.length)
  for (let i = 0; i < bytes.length; i += 1) {
    buffer[i] = bytes.charCodeAt(i)
  }
  if (previewAudioUrl.value) {
    URL.revokeObjectURL(previewAudioUrl.value)
  }
  previewAudioUrl.value = URL.createObjectURL(new Blob([buffer], { type: mimeType }))
}

async function previewVoice() {
  previewLoading.value = true
  try {
    const result = await api.admin.ttsPersonas.voicePreview({
      voice_description: TTS_VOICE_CONTRACT.description,
      sample_text: TTS_VOICE_CONTRACT.sample,
    })
    const audio = result.data?.audio || result.data?.audio_base64 || result.data?.data
    if (result.ok && audio) {
      playBase64Audio(audio, result.data?.mime_type || 'audio/wav')
    } else {
      ElMessage.error(result.data?.detail || '试听生成失败')
    }
  } finally {
    previewLoading.value = false
  }
}
</script>

<template>
  <div class="tts-persona-manager">
    <header class="admin-hero">
      <div>
        <span class="kicker">TTS 契约</span>
        <h2>语音角色管理</h2>
        <p>小程序当前只保留“冰糖”美少女声线，四个导览身份共享同一声线，通过文本风格区分身份，避免出现中年男声或语速过慢的问题。</p>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="fetchPersonas">
          <el-icon><RefreshRight /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" :loading="syncing" @click="syncAll">同步四身份声线</el-button>
      </div>
    </header>

    <section class="voice-contract">
      <div class="voice-card">
        <span class="voice-icon">🍬</span>
        <div>
          <span class="kicker">唯一保留声线</span>
          <h3>{{ TTS_VOICE_CONTRACT.label }}</h3>
          <p>{{ TTS_VOICE_CONTRACT.description }}</p>
          <blockquote>{{ TTS_VOICE_CONTRACT.sample }}</blockquote>
          <div class="preview-row">
            <el-button type="primary" plain :loading="previewLoading" @click="previewVoice">
              <el-icon><VideoPlay /></el-icon>
              生成试听
            </el-button>
            <audio v-if="previewAudioUrl" :src="previewAudioUrl" controls autoplay />
          </div>
        </div>
      </div>
    </section>

    <el-table :data="rows" v-loading="loading || syncing" class="persona-table">
      <el-table-column label="身份" min-width="230">
        <template #default="{ row }">
          <div class="persona-cell">
            <span>{{ row.icon }}</span>
            <div>
              <strong>{{ row.name }}</strong>
              <em>{{ row.focusTitle }}</em>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="prompt" label="导览角度" min-width="280" />
      <el-table-column label="后端声线" width="180">
        <template #default="{ row }">
          <el-tag :type="row.synced ? 'success' : 'warning'" effect="plain">
            {{ row.backendVoice || '未配置' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="150">
        <template #default="{ row }">
          <el-tag :type="row.synced ? 'success' : 'warning'">
            {{ row.synced ? '已对齐' : '待同步' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click="syncPersona(row)">
            <el-icon><Headset /></el-icon>
            同步
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.tts-persona-manager {
  min-height: 100%;
  padding: 28px 34px 56px;
  background: linear-gradient(180deg, #fffdf9 0%, #f8f2ea 100%);
}

.admin-hero,
.voice-contract,
.persona-table {
  border-radius: 16px;
  box-shadow: 0 14px 36px rgba(77, 49, 31, 0.07);
}

.admin-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
  padding: 24px;
  border: 1px solid rgba(126, 91, 65, 0.16);
  background: #fffaf3;
}

.kicker {
  color: #c57548;
  font-size: 13px;
  font-weight: 700;
}

.admin-hero h2 {
  margin: 8px 0;
  color: #2f2118;
  font-size: 28px;
}

.admin-hero p {
  max-width: 760px;
  margin: 0;
  color: #7e6a59;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.voice-contract {
  margin-bottom: 18px;
  padding: 22px;
  border: 1px solid rgba(126, 91, 65, 0.16);
  background: rgba(255, 252, 247, 0.92);
}

.voice-card {
  display: grid;
  grid-template-columns: 76px 1fr;
  gap: 18px;
}

.voice-icon {
  display: grid;
  place-items: center;
  width: 76px;
  height: 76px;
  border-radius: 18px;
  background: #f2e4d2;
  font-size: 34px;
}

.voice-card h3 {
  margin: 6px 0;
  color: #2f2118;
  font-size: 23px;
}

.voice-card p {
  margin: 0;
  color: #756252;
  line-height: 1.7;
}

blockquote {
  margin: 14px 0 0;
  padding: 12px 14px;
  border-left: 3px solid #c57548;
  background: #f7efe6;
  color: #3b2b20;
}

.preview-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 14px;
}

.preview-row audio {
  width: 360px;
  max-width: 100%;
}

.persona-table {
  overflow: hidden;
}

.persona-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.persona-cell span {
  font-size: 28px;
}

.persona-cell strong,
.persona-cell em {
  display: block;
}

.persona-cell strong {
  color: #2f2118;
}

.persona-cell em {
  margin-top: 2px;
  color: #987d67;
  font-size: 13px;
  font-style: normal;
}
</style>
