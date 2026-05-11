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
const expandedPart = ref(null)

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
  expandedPart.value = null
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

function toggleExpand(partId) {
  expandedPart.value = expandedPart.value === partId ? null : partId
}

function specsEntries(specs) {
  if (!specs || typeof specs !== 'object') return []
  return Object.entries(specs)
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
        <div style="display:flex;align-items:center;gap:8px">
          <span style="color:var(--primary);font-size:16px">⊞</span>
          <span style="font-family:'Rajdhani',sans-serif;font-weight:600;font-size:15px;color:var(--text-primary)">
            匹配结果
          </span>
        </div>
        <span class="results-count">{{ results.length }} 条零件匹配</span>
      </div>

      <div class="result-grid" v-if="results.length">
        <div class="result-card"
          v-for="(r, i) in results" :key="r.part_id"
          :class="{ 'result-card--priority': r.is_high_priority, 'result-card--expanded': expandedPart === r.part_id }"
          :style="{ '--delay': i }"
          @click="toggleExpand(r.part_id)">
          <!-- Thumbnails row -->
          <div class="result-card-thumbnails">
            <img v-for="(url, ti) in r.thumbnail_urls" :key="ti"
              class="result-card-thumb" :src="url"
              @error="handleImgError">
          </div>
          <div class="result-card-body">
            <div class="result-card-meta">
              <span class="result-card-name">{{ r.name }}</span>
              <span class="result-card-category">{{ r.category }}</span>
              <span v-if="r.is_high_priority" class="result-card-priority-badge">★ 重点</span>
            </div>
            <div class="similarity-bar-wrap">
              <div class="similarity-bar">
                <div class="similarity-bar-fill"
                  :style="{ width: r.best_similarity + '%' }"></div>
              </div>
              <span class="similarity-value">{{ r.best_similarity.toFixed(1) }}%</span>
            </div>
          </div>

          <!-- Expanded detail -->
          <div class="part-detail" v-if="expandedPart === r.part_id">
            <div class="part-detail-section">
              <div class="part-detail-label">最佳匹配照片</div>
              <div style="display:flex;align-items:center;gap:8px">
                <img class="part-detail-best-photo" :src="r.best_photo_url"
                  @error="handleImgError">
                <span class="part-detail-angle">{{ r.best_photo_angle }}</span>
              </div>
            </div>
            <div class="part-detail-section" v-if="r.thumbnail_urls && r.thumbnail_urls.length">
              <div class="part-detail-label">全部照片 ({{ r.total_photos }})</div>
              <div class="part-detail-thumbnails">
                <img v-for="(url, ti) in r.thumbnail_urls" :key="ti"
                  class="part-detail-thumb" :src="url"
                  @error="handleImgError">
              </div>
            </div>
            <div class="part-detail-section" v-if="specsEntries(r.specs).length">
              <div class="part-detail-label">规格参数</div>
              <table class="specs-table">
                <tr v-for="[k, v] in specsEntries(r.specs)" :key="k">
                  <td class="specs-table-key">{{ k }}</td>
                  <td class="specs-table-value">{{ v }}</td>
                </tr>
              </table>
            </div>
            <div class="part-detail-section" v-if="r.description">
              <div class="part-detail-label">描述</div>
              <div class="part-detail-desc">{{ r.description }}</div>
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

<style scoped>
.result-card--priority {
  border-color: var(--accent-dim);
  background: rgba(212, 168, 67, 0.04);
}
.result-card--priority:hover {
  border-color: var(--accent);
  box-shadow: 0 4px 20px rgba(212, 168, 67, 0.15);
}

.result-card--expanded {
  border-color: var(--primary);
  cursor: default;
}

.result-card {
  cursor: pointer;
}

.result-card-thumbnails {
  display: flex;
  gap: 4px;
  padding: 12px 12px 0;
  overflow: hidden;
}

.result-card-thumb {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: var(--surface-2);
}

.result-card-name {
  font-family: 'Rajdhani', sans-serif;
  font-weight: 700;
  font-size: 15px;
  color: var(--text-primary);
}

.result-card-priority-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: var(--accent);
  background: rgba(212, 168, 67, 0.12);
  border: 1px solid var(--accent-dim);
  padding: 2px 6px;
  border-radius: 3px;
}

.part-detail {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  animation: fadeIn 0.3s ease forwards;
}

.part-detail-section {
  margin-bottom: 12px;
}

.part-detail-section:last-child {
  margin-bottom: 0;
}

.part-detail-label {
  font-family: 'Rajdhani', sans-serif;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.part-detail-best-photo {
  width: 160px;
  height: 120px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface-2);
}

.part-detail-angle {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-muted);
}

.part-detail-thumbnails {
  display: flex;
  gap: 6px;
  overflow-x: auto;
}

.part-detail-thumb {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: var(--surface-2);
  flex-shrink: 0;
}

.specs-table {
  width: 100%;
  border-collapse: collapse;
}

.specs-table td {
  padding: 4px 10px;
  border: 1px solid var(--border);
  font-size: 13px;
}

.specs-table-key {
  font-family: 'Rajdhani', sans-serif;
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--surface-2);
  width: 120px;
}

.specs-table-value {
  font-family: 'JetBrains Mono', monospace;
  color: var(--accent);
  font-weight: 500;
}

.part-detail-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>