<script setup>
import { ref } from 'vue'
import api from '../api'
import { useSystemStore } from '../stores/system'

const system = useSystemStore()
const queryImage = ref(null)
const queryPreview = ref('')
const topK = ref(10)
const isDragOver = ref(false)
const isSearching = ref(false)
const results = ref([])
const queryCategory = ref(null)
const degraded = ref(false)
const searchDone = ref(false)
const emptyMessage = ref('')
const fileInput = ref(null)

function triggerFileInput() { fileInput.value.click() }

function handleFileSelect(e) {
  const f = e.target.files[0]
  if (f && f.type.startsWith('image/')) setQueryImage(f)
  e.target.value = ''
}

function handleDrop(e) {
  isDragOver.value = false
  const f = Array.from(e.dataTransfer.files).find(f => f.type.startsWith('image/'))
  if (f) setQueryImage(f)
}

function setQueryImage(f) {
  if (queryPreview.value) URL.revokeObjectURL(queryPreview.value)
  queryImage.value = f
  queryPreview.value = URL.createObjectURL(f)
  results.value = []
  queryCategory.value = null
  degraded.value = false
  searchDone.value = false
}

async function doSearch() {
  if (!queryImage.value) return
  isSearching.value = true
  system.setScanning(true)
  results.value = []
  const formData = new FormData()
  formData.append('image', queryImage.value)
  formData.append('top_k', topK.value)
  try {
    const res = await api.post('/search/query', formData)
    results.value = res.data.results
    queryCategory.value = res.data.query_category
    degraded.value = res.data.degraded
    emptyMessage.value = res.data.message
  } catch (err) {
    emptyMessage.value = '检索失败：' + (err.response?.data?.detail || err.message)
  } finally {
    isSearching.value = false
    system.setScanning(false)
    searchDone.value = true
  }
}

function similarityPercent(sim) {
  if (!results.value.length) return 0
  const best = Math.min(...results.value.map(r => r.similarity))
  const worst = Math.max(...results.value.map(r => r.similarity))
  if (worst <= best) return sim <= best ? 100 : 0
  return Math.max(0, Math.min(100, (1 - (sim - best) / (worst - best)) * 100))
}

function formatSimilarity(sim) {
  if (!results.value.length) return '0%'
  const best = Math.min(...results.value.map(r => r.similarity))
  const worst = Math.max(...results.value.map(r => r.similarity))
  if (worst <= best) return sim <= best ? '100%' : '0%'
  const pct = Math.max(0, Math.min(100, (1 - (sim - best) / (worst - best)) * 100))
  return pct.toFixed(1) + '%'
}

function handleImgError(e) {
  e.target.src = ''
  e.target.style.background = 'var(--surface-2)'
  e.target.alt = '图片加载失败'
}
</script>

<template>
  <div class="search-layout">
    <!-- Left: Query Upload -->
    <div>
      <div class="panel">
        <div class="panel-header">
          <span class="panel-header-icon">◉</span>
          <span class="panel-title">查询输入</span>
        </div>
        <div class="panel-body">
          <div class="upload-zone"
            :class="{ 'drag-over': isDragOver }"
            @click="triggerFileInput"
            @dragover.prevent="isDragOver = true"
            @dragleave="isDragOver = false"
            @drop.prevent="handleDrop"
            style="padding:20px">
            <template v-if="!queryImage">
              <div class="upload-zone-icon" style="font-size:28px">◉</div>
              <div class="upload-zone-text">上传查询图片</div>
              <input type="file" ref="fileInput" accept="image/*"
                @change="handleFileSelect" style="display:none">
            </template>
            <template v-else>
              <img class="search-query-img" :src="queryPreview">
              <input type="file" ref="fileInput" accept="image/*"
                @change="handleFileSelect" style="display:none">
            </template>
          </div>
          <div style="margin-top:12px">
            <div class="form-group">
              <label class="form-label">返回数量 Top-K</label>
              <input class="form-input" v-model.number="topK" type="number" min="1" max="50">
            </div>
          </div>
          <button class="btn btn-primary" style="width:100%"
            :disabled="!queryImage || isSearching"
            @click="doSearch">
            <span v-if="isSearching" class="loading-dots">正在检索</span>
            <span v-else>⬡ 开始检索</span>
          </button>
          <div v-if="queryCategory" class="search-category-badge" style="margin-top:12px">
            百炼判断: {{ queryCategory }}
          </div>
          <div v-if="degraded" class="search-category-badge search-degraded-badge" style="margin-top:8px">
            ⚠ 降级模式：全库检索
          </div>
        </div>
      </div>
    </div>

    <!-- Right: Results -->
    <div>
      <div class="results-header" v-if="results.length">
        <div class="panel-header-icon" style="color:var(--primary);font-size:16px">⊞</div>
        <span style="font-family:'Rajdhani',sans-serif;font-weight:600;font-size:15px;color:var(--text-primary)">
          匹配结果
        </span>
        <span class="results-count">{{ results.length }} 条匹配</span>
      </div>

      <div class="result-grid" v-if="results.length">
        <div class="result-card" v-for="(r, i) in results" :key="r.id"
          :style="{ '--delay': i }">
          <img class="result-card-image" :src="r.image_url"
            @error="handleImgError">
          <div class="result-card-body">
            <div class="result-card-meta">
              <span class="result-card-category">{{ r.category }}</span>
              <span class="result-card-spec">{{ r.specification }}</span>
            </div>
            <div class="result-card-desc" v-if="r.description">{{ r.description }}</div>
            <div class="similarity-bar-wrap">
              <div class="similarity-bar">
                <div class="similarity-bar-fill"
                  :style="{ width: similarityPercent(r.similarity) + '%' }"></div>
              </div>
              <span class="similarity-value">{{ formatSimilarity(r.similarity) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="empty-state" v-if="searchDone && !results.length">
        <div class="empty-state-icon">⊘</div>
        <div class="empty-state-text">{{ emptyMessage }}</div>
      </div>

      <div class="empty-state" v-if="!searchDone && !results.length">
        <div class="empty-state-icon">◉</div>
        <div class="empty-state-text">上传查询图片开始检索</div>
      </div>
    </div>
  </div>
</template>