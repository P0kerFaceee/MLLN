<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'
import { useSystemStore } from '../stores/system'

const system = useSystemStore()
const items = ref([])
const activeCategory = ref(null)

const filteredItems = computed(() => {
  if (!activeCategory.value) return items.value
  return items.value.filter(i => i.category === activeCategory.value)
})

async function loadItems() {
  try {
    const res = await api.get('/warehouse/list')
    items.value = res.data.items
  } catch (err) {
    console.error('Failed to load warehouse items', err)
  }
}

function handleImgError(e) {
  e.target.src = ''
  e.target.style.background = 'var(--surface-2)'
  e.target.alt = '图片加载失败'
}

onMounted(() => loadItems())
</script>

<template>
  <div class="panel">
    <div class="panel-header">
      <span class="panel-header-icon">⊞</span>
      <span class="panel-title">仓库底库浏览</span>
      <span class="panel-badge">{{ items.length }} 条记录</span>
      <button class="btn btn-outline" style="margin-left:auto;padding:6px 12px;font-size:12px"
        @click="loadItems">↻ 刷新</button>
    </div>
    <div class="panel-body">
      <!-- Category Filter -->
      <div class="flex-row gap-8 mb-16">
        <button class="btn btn-outline" style="padding:5px 12px;font-size:12px"
          :class="{ 'btn-accent': activeCategory === null }"
          @click="activeCategory = null">全部</button>
        <button class="btn btn-outline" style="padding:5px 12px;font-size:12px"
          v-for="cat in system.categories" :key="cat"
          :class="{ 'btn-accent': activeCategory === cat }"
          @click="activeCategory = cat">{{ cat }}</button>
      </div>

      <!-- Items Grid -->
      <div class="result-grid" v-if="filteredItems.length">
        <div class="result-card" v-for="(item, i) in filteredItems" :key="item.id"
          :style="{ '--delay': i }">
          <img class="result-card-image" :src="item.image_url"
            @error="handleImgError">
          <div class="result-card-body">
            <div class="result-card-meta">
              <span class="result-card-category">{{ item.category }}</span>
              <span class="result-card-spec">{{ item.specification }}</span>
            </div>
            <div class="result-card-desc" v-if="item.description">{{ item.description }}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-muted)">
              ID:{{ item.id }} · {{ item.created_at || '' }}
            </div>
          </div>
        </div>
      </div>

      <div class="empty-state" v-if="!filteredItems.length && items.length">
        <div class="empty-state-icon">⊘</div>
        <div class="empty-state-text">该类别下暂无记录</div>
      </div>

      <div class="empty-state" v-if="!items.length">
        <div class="empty-state-icon">⊞</div>
        <div class="empty-state-text">仓库为空，请先在学习端上传零件数据</div>
      </div>
    </div>
  </div>
</template>