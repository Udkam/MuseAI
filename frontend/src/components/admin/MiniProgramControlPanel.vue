<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Document,
  MapLocation,
  Monitor,
  Refresh,
  Search,
} from '@element-plus/icons-vue'
import { api } from '../../api/index.js'

const router = useRouter()
const loading = ref(false)
const fetchErrors = ref([])

const halls = ref([])
const exhibits = ref([])
const prompts = ref([])
const ttsPersonas = ref([])
const healthStatus = ref('unknown')
const readyStatus = ref('unknown')

const expectedHalls = [
  { slug: 'basic-exhibition-hall', name: '基本陈列展厅', type: '常开', owner: '展厅设置' },
  { slug: 'site-protection-hall', name: '遗址保护大厅', type: '常开', owner: '展厅设置' },
  { slug: 'kiln-hall', name: '陶窑展厅', type: '常开', owner: '展厅设置' },
  { slug: 'prehistoric-workshop', name: '史前工坊', type: '常开', owner: '展厅设置' },
  { slug: 'banpo-girl-sculpture', name: '半坡姑娘雕塑', type: '常开', owner: '展厅设置' },
  { slug: 'education-center', name: '教研中心', type: '常开', owner: '展厅设置' },
  { slug: 'peony-garden', name: '牡丹园', type: '常开', owner: '展厅设置' },
  { slug: 'temporary-hall-1', name: '临展厅一', type: '临展', owner: '展厅设置' },
  { slug: 'temporary-hall-2', name: '临展厅二', type: '临展', owner: '展厅设置' },
]

const personaContract = [
  { code: 'A', personaId: 'A', label: '考古研究员', report: '半坡考古研究报告', route: '考古研究路线' },
  { code: 'B', personaId: 'student/default', label: '研学记录员', report: '半坡研学记录报告', route: '研学记录路线' },
  { code: 'C', personaId: 'historian', label: '历史追问者', report: '半坡历史追问报告', route: '历史追问路线' },
  { code: 'D', personaId: 'artifact', label: '器物研究员', report: '半坡器物观察报告', route: '器物观察路线' },
]

const flowRows = computed(() => [
  {
    name: '入口问卷与四身份',
    miniapp: 'onboarding -> persona-reveal -> route',
    backend: '/tour/sessions, persona A/B/C/D',
    control: '提示词管理、语音角色管理',
    status: ttsPersonas.value.length >= 4 ? 'ok' : 'warn',
    note: ttsPersonas.value.length >= 4 ? '四身份语音配置已覆盖' : 'TTS 身份配置少于 4 个',
    actions: [
      { label: '看提示词', path: '/admin/prompts' },
      { label: '看语音角色', path: '/admin/tts-personas' },
    ],
  },
  {
    name: 'AI 策展路线',
    miniapp: 'route 页先展示可用路线，再接入 AI plan',
    backend: '/curator/plan-tour',
    control: '提示词管理、LLM 调用追踪、路线管理',
    status: healthStatus.value === 'ok' ? 'ok' : 'warn',
    note: '小程序实际优先使用 curator plan；路线管理用于人工维护和兜底参考',
    actions: [
      { label: '路线管理', path: '/admin/tour-paths' },
      { label: '调用追踪', path: '/admin/llm-traces' },
    ],
  },
  {
    name: '展厅选择与到访统计',
    miniapp: 'hall 选择、tour events、report halls_visited',
    backend: '/tour/halls, /tour/sessions/:id/events, /report',
    control: '展厅设置',
    status: missingExpectedHalls.value.length ? 'warn' : 'ok',
    note: missingExpectedHalls.value.length
      ? `缺少 ${missingExpectedHalls.value.length} 个小程序约定展厅`
      : '展厅 slug 与小程序常用顺序可对齐',
    actions: [{ label: '展厅设置', path: '/admin/halls' }],
  },
  {
    name: '展品搜索与拍照识别',
    miniapp: 'exhibit-scan 文字搜索/OCR 匹配 -> exhibit-detail',
    backend: '/exhibits, /exhibits/:id',
    control: '展品管理、知识库管理',
    status: exhibits.value.length ? 'ok' : 'warn',
    note: exhibits.value.length ? '展品 API 有数据可供搜索和 OCR 匹配' : '当前未读取到展品数据',
    actions: [
      { label: '展品管理', path: '/admin/exhibits' },
      { label: '知识库管理', path: '/admin/documents' },
    ],
  },
  {
    name: '建议条与 AI 回答',
    miniapp: 'tour suggestions Phase1/Phase2, SSE Markdown',
    backend: '/tour/sessions/:id/chat/stream, RAG prompts',
    control: '提示词管理、LLM 调用追踪',
    status: prompts.value.length ? 'ok' : 'warn',
    note: '建议条即时规则在小程序端；回答风格和 RAG 可通过提示词与追踪排查',
    actions: [
      { label: '提示词管理', path: '/admin/prompts' },
      { label: 'LLM 追踪', path: '/admin/llm-traces' },
    ],
  },
  {
    name: '报告与 Reflection Engine',
    miniapp: 'report 页直接渲染 halls_visited/highlights/reflection/record_notes',
    backend: '/tour/sessions/:id/report',
    control: '提示词管理、LLM 调用追踪',
    status: healthStatus.value === 'ok' ? 'ok' : 'warn',
    note: '报告主要由事件、展厅、展品和规则式 reflection 组成，不新增独立后台表',
    actions: [
      { label: '提示词管理', path: '/admin/prompts' },
      { label: '调用追踪', path: '/admin/llm-traces' },
    ],
  },
  {
    name: 'TTS 手动播报',
    miniapp: 'tour 页手动播放 AI 回复语音',
    backend: '/tts/synthesize',
    control: '语音角色管理',
    status: hasBingtangVoice.value ? 'ok' : 'warn',
    note: hasBingtangVoice.value ? '当前后台只保留冰糖声线配置' : '未检测到冰糖声线配置',
    actions: [{ label: '语音角色管理', path: '/admin/tts-personas' }],
  },
])

const quickActions = [
  { title: '维护展厅顺序', desc: '同步小程序选择页、路线页和报告统计使用的 canonical slug。', icon: MapLocation, path: '/admin/halls' },
  { title: '维护展品与 OCR 匹配', desc: '展品名称、分类、展厅归属会直接影响搜展品和拍照识别结果。', icon: Search, path: '/admin/exhibits' },
  { title: '调整导览提示词', desc: '控制 AI 回答风格、RAG 解释方式和报告文本边界。', icon: Document, path: '/admin/prompts' },
  { title: '排查线上回答', desc: '按调用记录查看 route、tour、report 的模型输入输出和错误。', icon: Monitor, path: '/admin/llm-traces' },
]

const missingExpectedHalls = computed(() => {
  const current = new Set(halls.value.map((hall) => hall.slug))
  return expectedHalls.filter((hall) => !current.has(hall.slug))
})

const inactiveExpectedHalls = computed(() => {
  const bySlug = new Map(halls.value.map((hall) => [hall.slug, hall]))
  return expectedHalls.filter((hall) => bySlug.has(hall.slug) && bySlug.get(hall.slug)?.is_active === false)
})

const hasBingtangVoice = computed(() => {
  if (!ttsPersonas.value.length) return false
  return ttsPersonas.value.every((item) => !item.voice || item.voice === '冰糖')
})

const dashboardStats = computed(() => [
  {
    label: '服务状态',
    value: healthStatus.value === 'ok' ? '正常' : '待检查',
    desc: readyStatus.value === 'ok' ? 'health / ready 均可用' : 'ready 状态未确认',
    type: healthStatus.value === 'ok' ? 'success' : 'warning',
  },
  {
    label: '展厅契约',
    value: `${expectedHalls.length - missingExpectedHalls.value.length}/${expectedHalls.length}`,
    desc: inactiveExpectedHalls.value.length
      ? `${inactiveExpectedHalls.value.length} 个约定展厅未启用`
      : '按小程序 canonical slug 检查',
    type: missingExpectedHalls.value.length || inactiveExpectedHalls.value.length ? 'warning' : 'success',
  },
  {
    label: '展品数据',
    value: String(exhibits.value.length),
    desc: '影响展品浏览、搜展品和 OCR fallback',
    type: exhibits.value.length ? 'success' : 'warning',
  },
  {
    label: '提示词',
    value: String(prompts.value.length),
    desc: '覆盖 RAG、策展、报告与语音人设',
    type: prompts.value.length ? 'success' : 'warning',
  },
])

async function safeLoad(label, loader) {
  try {
    const result = await loader()
    if (!result?.ok) {
      fetchErrors.value.push(`${label}: ${result?.data?.detail || result?.status || '失败'}`)
      return null
    }
    return result.data
  } catch (err) {
    fetchErrors.value.push(`${label}: ${err instanceof Error ? err.message : '失败'}`)
    return null
  }
}

async function fetchDashboard() {
  loading.value = true
  fetchErrors.value = []
  try {
    const [health, ready, hallData, exhibitData, promptData, ttsData] = await Promise.all([
      safeLoad('健康检查', () => api.health()),
      safeLoad('就绪检查', () => api.ready()),
      safeLoad('展厅设置', () => api.admin.listHalls({ include_inactive: 'true' })),
      safeLoad('展品数据', () => api.admin.listExhibits({ limit: 200 })),
      safeLoad('提示词', () => api.admin.prompts.list({ include_inactive: 'true' })),
      safeLoad('语音角色', () => api.admin.ttsPersonas.list()),
    ])

    healthStatus.value = health ? 'ok' : 'error'
    readyStatus.value = ready ? 'ok' : 'error'
    halls.value = hallData?.halls || []
    exhibits.value = exhibitData?.exhibits || []
    prompts.value = promptData?.prompts || []
    ttsPersonas.value = ttsData?.personas || []
  } finally {
    loading.value = false
  }
}

function go(path) {
  router.push(path)
}

function flowTagType(status) {
  return status === 'ok' ? 'success' : 'warning'
}

function flowTagText(status) {
  return status === 'ok' ? '已对齐' : '需检查'
}

onMounted(fetchDashboard)
</script>

<template>
  <div class="mini-program-control" v-loading="loading">
    <section class="control-header">
      <div>
        <p class="eyebrow">MuseAI 管理端</p>
        <h1>小程序闭环控制台</h1>
        <p class="subtitle">
          按小程序实际链路检查后台控制点：问卷、路线、展厅、展品、建议条、TTS、报告与 Reflection Engine。
        </p>
      </div>
      <el-button type="primary" @click="fetchDashboard">
        <el-icon><Refresh /></el-icon>
        刷新状态
      </el-button>
    </section>

    <el-alert
      v-if="fetchErrors.length"
      type="warning"
      :closable="false"
      show-icon
      class="status-alert"
    >
      <template #title>
        有 {{ fetchErrors.length }} 项状态未读取成功，通常是登录权限、后端服务或网络问题。
      </template>
      <div class="error-list">
        <span v-for="item in fetchErrors" :key="item">{{ item }}</span>
      </div>
    </el-alert>

    <section class="stat-grid">
      <article v-for="stat in dashboardStats" :key="stat.label" class="stat-card">
        <div class="stat-label">{{ stat.label }}</div>
        <div class="stat-value">{{ stat.value }}</div>
        <el-tag size="small" :type="stat.type">{{ stat.desc }}</el-tag>
      </article>
    </section>

    <section class="panel-section">
      <div class="section-title">
        <div>
          <h2>闭环能力对齐</h2>
          <p>小程序端每个功能都必须能在后台找到对应的数据、配置或排查入口。</p>
        </div>
      </div>

      <el-table :data="flowRows" border class="flow-table">
        <el-table-column prop="name" label="小程序能力" min-width="160">
          <template #default="{ row }">
            <div class="flow-name">{{ row.name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="miniapp" label="小程序链路" min-width="220" />
        <el-table-column prop="backend" label="后端契约" min-width="220" />
        <el-table-column prop="control" label="管理端控制点" min-width="180" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="flowTagType(row.status)" size="small">{{ flowTagText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="说明" min-width="240" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <el-button
                v-for="action in row.actions"
                :key="action.path + action.label"
                size="small"
                @click="go(action.path)"
              >
                {{ action.label }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="two-column">
      <div class="panel-section">
        <div class="section-title compact">
          <div>
            <h2>四身份契约</h2>
            <p>与小程序 persona、报告标题和路线主题保持一致。</p>
          </div>
          <el-button text type="primary" @click="go('/admin/tts-personas')">
            管理语音角色
          </el-button>
        </div>
        <el-table :data="personaContract" border size="small">
          <el-table-column prop="code" label="后端" width="70" />
          <el-table-column prop="personaId" label="前端 personaId" min-width="120" />
          <el-table-column prop="label" label="展示名" min-width="110" />
          <el-table-column prop="route" label="路线主题" min-width="130" />
          <el-table-column prop="report" label="报告标题" min-width="150" />
        </el-table>
      </div>

      <div class="panel-section">
        <div class="section-title compact">
          <div>
            <h2>展厅 slug 契约</h2>
            <p>报告统计、路线、展品筛选都应使用这些 canonical slug。</p>
          </div>
          <el-button text type="primary" @click="go('/admin/halls')">
            管理展厅
          </el-button>
        </div>
        <el-table :data="expectedHalls" border size="small" max-height="360">
          <el-table-column prop="name" label="中文名" min-width="130" />
          <el-table-column prop="slug" label="canonical slug" min-width="190" />
          <el-table-column prop="type" label="类型" width="80" />
          <el-table-column label="后台状态" width="100">
            <template #default="{ row }">
              <el-tag
                v-if="halls.some((hall) => hall.slug === row.slug && hall.is_active !== false)"
                type="success"
                size="small"
              >
                启用
              </el-tag>
              <el-tag
                v-else-if="halls.some((hall) => hall.slug === row.slug)"
                type="warning"
                size="small"
              >
                未启用
              </el-tag>
              <el-tag v-else type="danger" size="small">缺失</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <section class="quick-grid">
      <button
        v-for="item in quickActions"
        :key="item.title"
        type="button"
        class="quick-card"
        @click="go(item.path)"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span class="quick-title">{{ item.title }}</span>
        <span class="quick-desc">{{ item.desc }}</span>
      </button>
    </section>
  </div>
</template>

<style scoped>
.mini-program-control {
  padding: 24px;
  display: grid;
  gap: 18px;
  background: var(--el-bg-color-page);
  min-height: 100%;
}

.control-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--el-color-primary);
  font-weight: 600;
  font-size: 13px;
}

h1,
h2 {
  margin: 0;
  color: var(--el-text-color-primary);
}

h1 {
  font-size: 26px;
  line-height: 1.25;
}

h2 {
  font-size: 17px;
}

.subtitle,
.section-title p {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  line-height: 1.55;
}

.status-alert {
  border-radius: 8px;
}

.error-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}

.error-list span {
  font-size: 12px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stat-card,
.panel-section {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  box-shadow: var(--el-box-shadow-lighter);
}

.stat-card {
  padding: 16px;
  display: grid;
  gap: 8px;
}

.stat-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.panel-section {
  padding: 16px;
  min-width: 0;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}

.section-title.compact {
  align-items: center;
}

.flow-name {
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.action-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.two-column {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr);
  gap: 18px;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.quick-card {
  text-align: left;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
  color: var(--el-text-color-primary);
  border-radius: 8px;
  padding: 16px;
  min-height: 112px;
  cursor: pointer;
  display: grid;
  gap: 8px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.quick-card:hover {
  border-color: var(--el-color-primary);
  box-shadow: var(--el-box-shadow-light);
}

.quick-card .el-icon {
  font-size: 22px;
  color: var(--el-color-primary);
}

.quick-title {
  font-weight: 700;
}

.quick-desc {
  color: var(--el-text-color-secondary);
  line-height: 1.5;
  font-size: 13px;
}

@media (max-width: 1180px) {
  .stat-grid,
  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .two-column {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .mini-program-control {
    padding: 16px;
  }

  .control-header,
  .section-title {
    flex-direction: column;
  }

  .stat-grid,
  .quick-grid {
    grid-template-columns: 1fr;
  }
}
</style>
