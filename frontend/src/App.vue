<script setup>
import { useSystemStore } from './stores/system'
import { useRoute } from 'vue-router'
import { watch, onMounted } from 'vue'

const system = useSystemStore()
const route = useRoute()

onMounted(() => system.fetchHealth())
watch(route, () => system.fetchHealth())
</script>

<template>
  <div class="scan-overlay" v-if="system.isScanning"></div>
  <header class="sys-header">
    <div class="header-brand">
      <div class="brand-icon">
        <svg width="28" height="28" viewBox="0 0 28 28">
          <rect x="2" y="2" width="8" height="8" fill="var(--accent)" rx="1"/>
          <rect x="12" y="2" width="8" height="8" fill="var(--primary)" rx="1"/>
          <rect x="22" y="2" width="4" height="8" fill="var(--text-muted)" rx="1"/>
          <rect x="2" y="12" width="14" height="4" fill="var(--primary)" rx="1"/>
          <rect x="18" y="12" width="8" height="4" fill="var(--accent)" rx="1"/>
          <rect x="2" y="18" width="24" height="8" fill="var(--text-secondary)" rx="1"/>
        </svg>
      </div>
      <div class="brand-text">
        <span class="brand-name">MLLN</span>
        <span class="brand-sub">工业仓库物流识别</span>
      </div>
    </div>
    <nav class="header-nav">
      <router-link to="/learn" class="nav-link" :class="{ active: route.path === '/learn' }">
        <span class="nav-icon">◈</span> 学习端
      </router-link>
      <router-link to="/search" class="nav-link" :class="{ active: route.path === '/search' }">
        <span class="nav-icon">◉</span> 使用端
      </router-link>
      <router-link to="/warehouse" class="nav-link" :class="{ active: route.path === '/warehouse' }">
        <span class="nav-icon">⊞</span> 仓库
      </router-link>
    </nav>
    <div class="header-status">
      <div class="status-item">
        <span class="status-label">DB</span>
        <span class="status-value">{{ system.dbCount }}</span>
      </div>
      <div class="status-dot" :class="{ online: system.systemOnline }"></div>
    </div>
  </header>
  <main class="sys-main">
    <router-view />
  </main>
</template>