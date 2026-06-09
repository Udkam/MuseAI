<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../../api/index.js'
import { useAdmin } from '../../composables/useAdmin.js'
import {
  BANPO_HALLS,
  createHallPayload,
  getLegacyHallRows,
  mergeHallsWithContract,
  normalizeHallSlug,
} from '../../constants/banpo.js'

const { loading, createHall, updateHall } = useAdmin()

const rawHalls = ref([])
const halls = ref([])
const tableRef = ref(null)
const fetchLoading = ref(false)
const syncLoading = ref(false)
const dialogVisible = ref(false)
const formRef = ref(null)

const form = ref({
  slug: '',
  name: '',
  description: '',
  floor: 1,
  estimated_duration_minutes: 20,
  display_order: 10,
  is_active: true,
})

const rules = {
  name: [{ required: true, message: '请输入展厅名称', trigger: 'blur' }],
}

const pageLoading = computed(() => loading.value || fetchLoading.value || syncLoading.value)
const legacyRows = computed(() => getLegacyHallRows(rawHalls.value))
const backendMatchedCount = computed(() => halls.value.filter((hall) => hall.hasBackend).length)
const activeCount = computed(() => halls.value.filter((hall) => hall.is_active !== false).length)

onMounted(fetchHalls)

async function fetchHalls() {
  fetchLoading.value = true
  try {
    const result = await api.admin.listHalls({ include_inactive: 'true' })
    if (result.ok) {
      const records = result.data.halls || []
      rawHalls.value = records
      halls.value = mergeHallsWithContract(records)
      await nextTick()
      tableRef.value?.clearSelection?.()
    } else {
      ElMessage.error(result.data?.detail || '获取展厅失败')
    }
  } finally {
    fetchLoading.value = false
  }
}

function findBackendHall(canonicalSlug) {
  return rawHalls.value.find((hall) => normalizeHallSlug(hall.slug || hall.hall || hall.hall_slug) === canonicalSlug)
}

async function syncOneHall(row) {
  const payload = createHallPayload(row.contract || row)
  const current = findBackendHall(payload.slug)
  const { slug, ...updatePayload } = payload
  const result = current
    ? await updateHall(current.slug || payload.slug, updatePayload)
    : await createHall(payload)

  if (result.ok) {
    ElMessage.success(`${payload.name} 已同步`)
    await fetchHalls()
  } else {
    ElMessage.error(result.data?.detail || `${payload.name} 同步失败`)
  }
}

async function syncAllHalls() {
  syncLoading.value = true
  let successCount = 0
  let failedCount = 0

  try {
    for (const hall of BANPO_HALLS) {
      const payload = createHallPayload(hall)
      const current = findBackendHall(payload.slug)
      const { slug, ...updatePayload } = payload
      const result = current
        ? await updateHall(current.slug || payload.slug, updatePayload)
        : await createHall(payload)

      if (result.ok) {
        successCount += 1
      } else {
        failedCount += 1
      }
    }

    await fetchHalls()

    if (failedCount) {
      ElMessage.warning(`已同步 ${successCount} 个展厅，${failedCount} 个失败`)
    } else {
      ElMessage.success(`已同步 ${successCount} 个半坡展厅`)
    }
  } finally {
    syncLoading.value = false
  }
}

function handleEdit(row) {
  form.value = {
    slug: row.slug,
    name: row.name,
    description: row.description || '',
    floor: row.floor || 1,
    estimated_duration_minutes: row.estimated_duration_minutes || 20,
    display_order: row.display_order || 0,
    is_active: row.is_active !== false,
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  const { slug, ...payload } = form.value
  const current = findBackendHall(slug)
  const result = current
    ? await updateHall(current.slug || slug, payload)
    : await createHall({ slug, ...payload })

  if (result.ok) {
    ElMessage.success('展厅已保存')
    dialogVisible.value = false
    await fetchHalls()
  } else {
    ElMessage.error(result.data?.detail || '保存失败')
  }
}
</script>

<template>
  <div class="hall-manager">
    <header class="admin-hero">
      <div>
        <span class="kicker">小程序契约</span>
        <h2>半坡展厅设置</h2>
        <p>这里维护的是小程序、路线、报告和展品搜索共用的 canonical hall slug。临展厅默认排在最后，旧馆名只保留兼容映射。</p>
      </div>
      <div class="hero-actions">
        <el-button :loading="fetchLoading" @click="fetchHalls">刷新</el-button>
        <el-button type="primary" :loading="syncLoading" @click="syncAllHalls">同步半坡展厅契约</el-button>
      </div>
    </header>

    <section class="stat-grid">
      <div class="stat-card">
        <span>契约展厅</span>
        <strong>{{ BANPO_HALLS.length }}</strong>
      </div>
      <div class="stat-card">
        <span>后端已匹配</span>
        <strong>{{ backendMatchedCount }}</strong>
      </div>
      <div class="stat-card">
        <span>当前启用</span>
        <strong>{{ activeCount }}</strong>
      </div>
      <div class="stat-card warn">
        <span>旧 slug 记录</span>
        <strong>{{ legacyRows.length }}</strong>
      </div>
    </section>

    <el-alert
      v-if="legacyRows.length"
      type="warning"
      :closable="false"
      show-icon
      class="legacy-alert"
      title="检测到旧展厅 slug"
    >
      <template #default>
        <div class="legacy-list">
          <span v-for="item in legacyRows" :key="item.slug">
            {{ item.name || item.slug }} -> {{ item.targetName }} ({{ item.targetSlug }})
          </span>
        </div>
      </template>
    </el-alert>

    <el-table
      ref="tableRef"
      :data="halls"
      row-key="slug"
      v-loading="pageLoading"
      class="contract-table"
    >
      <el-table-column label="展厅" min-width="300">
        <template #default="{ row }">
          <div class="hall-cell">
            <span class="hall-icon">{{ row.icon }}</span>
            <div>
              <div class="hall-name">{{ row.name }}</div>
              <div class="hall-desc">{{ row.description }}</div>
              <div class="hall-tags">
                <el-tag size="small" effect="plain">{{ row.type }}</el-tag>
                <el-tag size="small" type="info" effect="plain">{{ row.zone }}</el-tag>
              </div>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="slug" label="canonical slug" min-width="190" />
      <el-table-column prop="floor" label="楼层" width="90" />
      <el-table-column prop="estimated_duration_minutes" label="建议时长" width="110">
        <template #default="{ row }">{{ row.estimated_duration_minutes }} 分钟</template>
      </el-table-column>
      <el-table-column prop="display_order" label="排序" width="90" />
      <el-table-column label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="findBackendHall(row.slug) ? 'success' : 'warning'" effect="plain">
            {{ findBackendHall(row.slug) ? '已入库' : '待同步' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button type="primary" size="small" plain @click="syncOneHall(row)">同步</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="编辑展厅基础信息" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="展厅 slug">
          <el-input v-model="form.slug" disabled />
        </el-form-item>
        <el-form-item label="展厅名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="楼层">
              <el-input-number v-model="form.floor" :min="1" :max="5" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="建议时长">
              <el-input-number v-model="form.estimated_duration_minutes" :min="1" :max="120" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="排序">
              <el-input-number v-model="form.display_order" :min="0" :max="999" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.hall-manager {
  min-height: 100%;
  padding: 28px 34px 52px;
  background: linear-gradient(180deg, #fffdf9 0%, #f8f2ea 100%);
}

.admin-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;
  padding: 24px;
  border: 1px solid rgba(126, 91, 65, 0.16);
  border-radius: 16px;
  background: #fffaf3;
  box-shadow: 0 14px 36px rgba(77, 49, 31, 0.07);
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
  max-width: 720px;
  margin: 0;
  color: #7e6a59;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  white-space: nowrap;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.stat-card {
  padding: 18px;
  border: 1px solid rgba(126, 91, 65, 0.14);
  border-radius: 14px;
  background: rgba(255, 252, 247, 0.9);
}

.stat-card span {
  color: #957c67;
  font-size: 13px;
}

.stat-card strong {
  display: block;
  margin-top: 8px;
  color: #35261c;
  font-size: 28px;
}

.stat-card.warn strong {
  color: #b66c45;
}

.legacy-alert {
  margin-bottom: 18px;
}

.legacy-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
}

.contract-table {
  border-radius: 12px;
  overflow: hidden;
}

.hall-cell {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.hall-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: #f1e4d4;
  font-size: 22px;
  flex: 0 0 auto;
}

.hall-name {
  color: #2f2118;
  font-weight: 700;
}

.hall-desc {
  margin-top: 4px;
  color: #7b6758;
  line-height: 1.5;
}

.hall-tags {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

@media (max-width: 960px) {
  .admin-hero {
    flex-direction: column;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
