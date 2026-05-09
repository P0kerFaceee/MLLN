<script setup>
import { ref, computed } from 'vue'
import api from '../api'
import { useSystemStore } from '../stores/system'

const system = useSystemStore()
const files = ref([])
const category = ref('')
const specification = ref('')
const description = ref('')
const isDragOver = ref(false)
const isUploading = ref(false)
const uploadResults = ref([])
const fileInput = ref(null)
const maxFiles = 20

const canUpload = computed(() =>
  files.value.length > 0 && category.value.trim() && specification.value.trim()
)

function triggerFileInput() { fileInput.value.click() }

function handleFileSelect(e) {
  addFiles(Array.from(e.target.files))
  e.target.value = ''
}

function handleDrop(e) {
  isDragOver.value = false
  addFiles(Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/')))
}

function addFiles(newFiles) {
  const remaining = maxFiles - files.value.length
  const toAdd = newFiles.slice(0, remaining)
  toAdd.forEach(f => {
    f.preview = URL.createObjectURL(f)
    f.status = null
    f.statusText = ''
    f.id = 0
  })
  files.value = files.value.concat(toAdd)
}

function removeFile(index) {
  URL.revokeObjectURL(files.value[index].preview)
  files.value.splice(index, 1)
}

async function uploadAll() {
  isUploading.value = true
  uploadResults.value = []
  for (const f of files.value) {
    const formData = new FormData()
    formData.append('image', f)
    formData.append('category', category.value.trim())
    formData.append('specification', specification.value.trim())
    if (description.value.trim()) formData.append('description', description.value.trim())
    try {
      const res = await api.post('/learn/upload', formData)
      f.status = res.data.status
      f.id = res.data.id
      f.statusText = res.data.status === 'success' ? '入库成功' : '待审核'
    } catch {
      f.status = 'error'
      f.statusText = '上传失败'
    }
    uploadResults.value.push({
      name: f.name,
      preview: f.preview,
      status: f.status,
      statusText: f.statusText,
      id: f.id,
    })
  }
  isUploading.value = false
  system.fetchHealth()
}
</script>

<template>
  <div class="learn-layout">
    <!-- Left: Upload + Preview -->
    <div>
      <div class="panel">
        <div class="panel-header">
          <span class="panel-header-icon">◈</span>
          <span class="panel-title">图片上传</span>
          <span class="panel-badge">{{ files.length }} / {{ maxFiles }}</span>
        </div>
        <div class="panel-body">
          <div class="upload-zone"
            :class="{ 'drag-over': isDragOver }"
            @click="triggerFileInput"
            @dragover.prevent="isDragOver = true"
            @dragleave="isDragOver = false"
            @drop.prevent="handleDrop">
            <div class="upload-zone-icon">⬡</div>
            <div class="upload-zone-text">拖拽照片至此处 或 点击选择</div>
            <div class="upload-zone-sub">支持 JPG / PNG，最多 {{ maxFiles }} 张</div>
            <input type="file" ref="fileInput" multiple accept="image/*"
              @change="handleFileSelect" style="display:none">
          </div>
          <div class="preview-grid" v-if="files.length">
            <div class="preview-item" v-for="(f, i) in files" :key="i"
              :style="{ animationDelay: (i * 60) + 'ms' }">
              <img :src="f.preview">
              <button class="preview-remove" @click="removeFile(i)">×</button>
              <div class="preview-status" v-if="f.status" :class="f.status">{{ f.statusText }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Upload Results -->
      <div class="panel mt-16" v-if="uploadResults.length">
        <div class="panel-header">
          <span class="panel-header-icon">◉</span>
          <span class="panel-title">上传结果</span>
          <span class="panel-badge">{{ uploadResults.filter(r => r.status === 'success').length }} 成功</span>
        </div>
        <div class="panel-body">
          <div class="upload-list">
            <div class="upload-list-item" v-for="(r, i) in uploadResults" :key="i"
              :style="{ animationDelay: (i * 80) + 'ms' }">
              <img class="upload-list-thumb" :src="r.preview">
              <div class="upload-list-info">
                <div class="upload-list-name">{{ r.name }}</div>
                <div class="upload-list-detail">
                  {{ r.status === 'success' ? 'ID:' + r.id : r.statusText }}
                </div>
              </div>
              <span class="upload-list-status" :class="r.status">{{ r.statusText }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right: Metadata Form -->
    <div>
      <div class="panel">
        <div class="panel-header">
          <span class="panel-header-icon">⊕</span>
          <span class="panel-title">元数据</span>
        </div>
        <div class="panel-body">
          <div class="form-group">
            <label class="form-label">
              类别 <span class="form-label-required">●</span>
            </label>
            <input class="form-input" v-model="category"
              placeholder="例：压缩弹簧、夹线器、挑线簧">
          </div>
          <div class="form-group">
            <label class="form-label">
              规格 <span class="form-label-required">●</span>
            </label>
            <input class="form-input" v-model="specification"
              placeholder="例：压脚杆弹簧、M10x30">
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <textarea class="form-textarea" v-model="description"
              placeholder="零件的补充描述信息"></textarea>
          </div>
          <button class="btn btn-accent" style="width:100%"
            :disabled="!canUpload || isUploading"
            @click="uploadAll">
            <span v-if="isUploading" class="loading-dots">正在处理</span>
            <span v-else>⬡ 批量入库 {{ files.length }} 张</span>
          </button>
          <div style="text-align:center;margin-top:10px">
            <span style="font-size:12px;color:var(--text-muted)">
              每张图片将使用相同的类别和规格信息
            </span>
          </div>
        </div>
      </div>

      <!-- Quick Stats -->
      <div class="panel mt-16">
        <div class="panel-header">
          <span class="panel-header-icon">⊞</span>
          <span class="panel-title">底库状态</span>
        </div>
        <div class="panel-body" style="text-align:center">
          <div style="font-family:'JetBrains Mono',monospace;font-size:24px;color:var(--accent);font-weight:700">
            {{ system.dbCount }}
          </div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:4px">条记录</div>
          <div style="margin-top:8px;font-size:11px;color:var(--text-secondary)">
            {{ system.categories.join(' · ') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>