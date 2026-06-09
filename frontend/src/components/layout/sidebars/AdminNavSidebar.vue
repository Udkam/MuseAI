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
  background: #ffffff;
}

.sidebar-header {
  padding: 22px 18px 18px;
  border-bottom: 1px solid #dfe6e2;
  background: #f8faf9;
}

.sidebar-header p {
  margin: 0 0 4px;
  color: #a94c2c;
  font-size: 12px;
  font-weight: 700;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 20px;
  line-height: 1.25;
  color: #202725;
  letter-spacing: 0;
}

.admin-menu {
  flex: 1;
  border-right: 0;
  background: transparent;
  padding: 10px 8px 16px;
  overflow-y: auto;
}

.admin-menu :deep(.el-menu-item) {
  height: 42px;
  margin: 3px 0;
  border-radius: 6px;
  color: #46514e;
  font-size: 14px;
  font-weight: 500;
}

.admin-menu :deep(.el-menu-item .el-icon) {
  color: #6f7e78;
}

.admin-menu :deep(.el-menu-item:hover) {
  background: #edf5f1;
  color: #202725;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background: #496f60;
  color: #ffffff;
}

.admin-menu :deep(.el-menu-item.is-active .el-icon) {
  color: #ffffff;
}
</style>
