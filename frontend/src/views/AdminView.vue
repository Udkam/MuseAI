<script setup>
// Admin view - navigation is handled by AppSidebar.vue
</script>

<template>
  <div class="admin-view">
    <router-view />
  </div>
</template>

<style>
@import '../styles/admin.css';

.admin-view {
  min-height: 100%;
  background: #f5f7f8;
}
</style>
