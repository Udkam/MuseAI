<script setup>
import { Collection, Cpu, Document, MapLocation, Microphone, Monitor, OfficeBuilding } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const adminItems = [
  { path: '/admin/overview', label: '小程序闭环', icon: Monitor },
  { path: '/admin/documents', label: '知识库管理', icon: Document },
  { path: '/admin/halls', label: '展厅设置', icon: OfficeBuilding },
  { path: '/admin/exhibits', label: '展品管理', icon: Collection },
  { path: '/admin/tour-paths', label: '路线管理', icon: MapLocation },
  { path: '/admin/prompts', label: '提示词管理', icon: Document },
  { path: '/admin/tts-personas', label: '语音角色管理', icon: Microphone },
  { path: '/admin/llm-traces', label: 'LLM 调用追踪', icon: Cpu },
]
</script>

<template>
  <section class="sidebar-section admin-nav-sidebar">
    <header class="sidebar-header">
      <p>管理后台</p>
      <h3>半坡导览配置</h3>
    </header>

    <el-menu :default-active="route.path" router class="admin-menu">
      <el-menu-item v-for="item in adminItems" :key="item.path" :index="item.path">
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </el-menu-item>
    </el-menu>
  </section>
</template>

<style scoped>
.sidebar-section {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0;
  background: linear-gradient(180deg, rgba(250, 245, 237, 0.92), rgba(255, 252, 247, 0.98));
}

.sidebar-header {
  padding: var(--space-5) var(--space-4);
  border-bottom: 1px solid rgba(77, 51, 31, 0.08);
}

.sidebar-header p {
  margin: 0 0 4px;
  color: var(--color-accent);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
}

.sidebar-header h3 {
  margin: 0;
  font-size: var(--font-size-h4);
  color: var(--color-text-primary);
}

.admin-menu {
  flex: 1;
  border-right: 0;
  background: transparent;
}

.admin-menu :deep(.el-menu-item) {
  margin: 4px 10px;
  border-radius: 8px;
}
</style>
